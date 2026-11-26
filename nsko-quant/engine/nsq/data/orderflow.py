"""Real-time order flow.

Crypto: the Kraken public WebSocket v2 `trade` channel (wss://ws.kraken.com/v2) gives every trade
with its taker side, so volume here is true trade-by-trade exchange volume.
  - `orderflow_bubble`: a big aggressive order. Trades with the same timestamp and side are one
    taker order sweeping several price levels, so they are merged first; a bubble fires when the
    merged size is in the top `bubble_pct` percentile of recent orders (and >= a floor).
  - `profile_update`: the session volume profile (POC, VAH, VAL, LVNs, bins) every few seconds.

Gold: `TickProfile` counts broker price updates per price bin. That is a TICK-VOLUME profile:
CFD brokers report no exchange volume, so tick counts are only a proxy for activity.
"""
from __future__ import annotations

import asyncio
import json
import threading
import time
from collections import deque

import numpy as np
import pandas as pd

from . import profile
from .markets import info, norm
from .util import emit, log

KRAKEN_WS = "wss://ws.kraken.com/v2"


class OrderFlowEngine:
    def __init__(self, market: str, window_s: int = 4 * 3600, bubble_pct: float = 99.0, min_bubble: float = 0.0,
                 bins: int = 48, profile_every_s: float = 5.0, volume_kind: str = "exchange"):
        self.market = norm(market)
        self.window_s = window_s
        self.bubble_pct = bubble_pct
        self.min_bubble = min_bubble
        self.bins = bins
        self.profile_every_s = profile_every_s
        self.volume_kind = volume_kind
        self.trades: deque = deque()            # (ts, price, qty, side)
        self.order_sizes: deque = deque(maxlen=5000)
        self._pending: dict | None = None       # trades being merged into one taker order
        self._last_profile = 0.0
        self.bubbles = 0
        self.delta = 0.0                         # cumulative buy minus sell volume

    # taker order merge -> bubble decision
    def _flush(self) -> dict | None:
        o, self._pending = self._pending, None
        if not o:
            return None
        size = o["qty"]
        thr = self.min_bubble
        if len(self.order_sizes) >= 200:
            thr = max(thr, float(np.percentile(np.fromiter(self.order_sizes, float), self.bubble_pct)))
        self.order_sizes.append(size)
        if len(self.order_sizes) > 200 and size >= thr and size > 0:
            self.bubbles += 1
            ev = {"market": self.market, "price": o["vwap"] / size if size else o["price"], "size": size,
                  "side": o["side"], "ts": int(o["ts"] * 1000), "levels": o["n"], "threshold": thr,
                  "volume_kind": self.volume_kind}
            emit("orderflow_bubble", ev)
            return ev
        return None

    def on_trade(self, ts: float, price: float, qty: float, side: str) -> dict | None:
        """Feed one trade (ts in seconds, side = taker side 'buy'|'sell'). Returns a bubble if one fired."""
        bubble = None
        p = self._pending
        if p and (p["ts"] != ts or p["side"] != side):
            bubble = self._flush()
        if self._pending is None:
            self._pending = {"ts": ts, "side": side, "qty": 0.0, "vwap": 0.0, "price": price, "n": 0}
        self._pending["qty"] += qty
        self._pending["vwap"] += price * qty
        self._pending["n"] += 1
        self.trades.append((ts, price, qty, side))
        self.delta += qty if side == "buy" else -qty
        cut = ts - self.window_s
        while self.trades and self.trades[0][0] < cut:
            self.trades.popleft()
        if ts - self._last_profile >= self.profile_every_s:
            self._last_profile = ts
            self.emit_profile()
        return bubble

    def profile(self) -> dict:
        if not self.trades:
            return profile.from_trades([], [], self.bins, kind=self.volume_kind)
        arr = np.array([(t[1], t[2]) for t in self.trades])
        return profile.from_trades(arr[:, 0], arr[:, 1], self.bins, kind=self.volume_kind)

    def emit_profile(self) -> dict:
        pr = self.profile()
        payload = {"market": self.market, "poc": pr["poc"], "vah": pr["vah"], "val": pr["val"], "lvn": pr["lvn"],
                   "hvn": pr["hvn"], "bins": pr["bins"], "volume_kind": self.volume_kind, "delta": self.delta,
                   "label": "volume profile" if self.volume_kind == "exchange" else "tick-volume profile",
                   "window_s": self.window_s}
        emit("profile_update", payload)
        return payload


class TickProfile(OrderFlowEngine):
    """Gold / CFD: every broker price update counts as one tick of 'volume' (tick-volume profile).
    No bubbles: a tick count says nothing about order size."""

    def __init__(self, market: str = "XAU/USD", **kw):
        kw.setdefault("volume_kind", "tick")
        super().__init__(market, **kw)

    def on_tick(self, ts: float, price: float) -> None:
        self.trades.append((ts, price, 1.0, "tick"))
        cut = ts - self.window_s
        while self.trades and self.trades[0][0] < cut:
            self.trades.popleft()
        if ts - self._last_profile >= self.profile_every_s:
            self._last_profile = ts
            self.emit_profile()

    def on_trade(self, *a, **k):  # pragma: no cover - not meaningful for CFDs
        raise TypeError("CFDs have no trade stream; use on_tick (tick-volume profile)")


def parse_kraken_trade_msg(msg: dict) -> list[tuple[float, float, float, str, str]]:
    """Kraken WS v2 trade message -> [(ts_seconds, price, qty, side, symbol)]."""
    if msg.get("channel") != "trade" or msg.get("type") not in ("update", "snapshot"):
        return []
    out = []
    for d in msg.get("data", []):
        ts = pd.Timestamp(d["timestamp"]).timestamp()
        out.append((ts, float(d["price"]), float(d["qty"]), d["side"], d["symbol"]))
    return out


async def kraken_trade_stream(markets: list[str], engines: dict[str, OrderFlowEngine] | None = None,
                              stop: threading.Event | None = None, max_seconds: float | None = None) -> dict:
    """Subscribe to Kraken WS v2 trades and feed OrderFlowEngines. Reconnects with back-off."""
    try:
        import websockets  # BSD-3-Clause
    except ImportError as e:  # pragma: no cover
        raise RuntimeError("pip install websockets to use the live trade stream") from e
    engines = engines or {norm(m): OrderFlowEngine(m) for m in markets}
    sym_to_mkt = {info(m)["kraken_ws"]: norm(m) for m in markets if info(m).get("kraken_ws")}
    t0 = time.time()
    backoff = 1.0
    while not (stop and stop.is_set()) and not (max_seconds and time.time() - t0 > max_seconds):
        try:
            async with websockets.connect(KRAKEN_WS, ping_interval=20, open_timeout=15) as ws:
                await ws.send(json.dumps({"method": "subscribe",
                                          "params": {"channel": "trade", "symbol": list(sym_to_mkt), "snapshot": False}}))
                log("READ", f"Kraken trade stream live · {', '.join(sym_to_mkt)}")
                backoff = 1.0
                while not (stop and stop.is_set()):
                    if max_seconds and time.time() - t0 > max_seconds:
                        break
                    raw = await asyncio.wait_for(ws.recv(), timeout=60)
                    for ts, px, q, side, sym in parse_kraken_trade_msg(json.loads(raw)):
                        m = sym_to_mkt.get(sym)
                        if m:
                            engines[m].on_trade(ts, px, q, side)
        except Exception as e:  # network blocked or dropped: back off, then retry
            log("PAUSE", f"Kraken trade stream down ({type(e).__name__}); retrying in {int(backoff)} s")
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, 60)
    return {m: {"bubbles": e.bubbles, "trades_in_window": len(e.trades)} for m, e in engines.items()}


def start_stream_thread(markets: list[str]) -> tuple[threading.Thread, threading.Event, dict]:
    """Run the trade stream in a daemon thread. Returns (thread, stop_event, engines)."""
    stop = threading.Event()
    engines = {norm(m): OrderFlowEngine(m) for m in markets}
    th = threading.Thread(target=lambda: asyncio.run(kraken_trade_stream(markets, engines, stop)), daemon=True,
                          name="kraken-trades")
    th.start()
    return th, stop, engines
