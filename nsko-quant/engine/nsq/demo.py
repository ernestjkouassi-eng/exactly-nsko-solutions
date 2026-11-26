"""DEMO event source. Runs only while no data source or real broker is connected (setting "demo" true).

Emits the same event shapes as app/src/demo/sim.ts (tick, orderflow_bubble, ticker_log, source_added,
agent_handoff, variant_tested, budget_update) plus a demo trade card cycle (scan_hit ... exit_done).
EVERY payload carries "demo": true, so the app can flag every number as DEMO DATA.
engine_health is NOT faked here: it always comes from the real health monitor.
"""
from __future__ import annotations

import math
import random
import threading
import time

from .bus import publish

MARKETS = {"XAU/USD": (2648.4, .00045), "BTC/USD": (97240, .0011), "ETH/USD": (3612, .0013), "NVDA": (141.2, .0009), "AAPL": (232.6, .0006)}
IDEA_TYPES = ["Trend following", "Mean reversion", "Breakout", "Volatility", "Orderflow", "Seasonality", "Carry"]
AGENTS = ["JARVIS", "SCOUT", "READER", "WATCHER", "SUMMARISER 1", "SUMMARISER 2", "SUMMARISER 3", "TERM-CHECKER", "RECIPE-MAKER", "LAB", "RISK", "EXECUTOR"]
SEARCHES = ['GitHub "orderflow futures backtest"', 'arXiv "time-series momentum gold"', 'YouTube "London session XAU scalping"',
            'Web "VWAP reversion intraday"', 'GitHub "volume profile python"', 'arXiv "regime switching commodities"']
TITLES = ["Time-series momentum on index futures", "Order blocks and fair value gaps, explained", "Volatility breakout on gold, 4h",
          "Seasonality in precious metals", "Reading the volume profile like a market maker", "Opening-range breakout: does it still work?"]
RECIPES = ["Range-XAU", "Trend-XAU", "Sweep-XAU", "VWAP-Rev-BTC", "ORB-NVDA", "Breakout-ETH", "Carry-XAU", "OF-1-XAU", "Momentum-BTC"]
FAILS = ["Win rate too low", "R:R too low", "Too few trades", "Expectancy negative after costs", "Max drawdown too deep", "Doesn't work out-of-sample"]


def _emit(t: str, p: dict) -> None:
    publish(t, {**p, "demo": True})


class DemoSource:
    def __init__(self, seed: int = 20261126):
        self.rng = random.Random(seed)
        self.px = {k: v[0] for k, v in MARKETS.items()}
        self.tested = 1251
        self._stop = threading.Event()
        self._t: threading.Thread | None = None
        self.step = 0

    def g(self) -> float:
        return self.rng.gauss(0, 1)

    def start(self) -> None:
        if self._t and self._t.is_alive():
            return
        self._stop.clear()
        self._t = threading.Thread(target=self._run, name="nsq-demo", daemon=True)
        self._t.start()

    def stop(self) -> None:
        self._stop.set()

    @property
    def running(self) -> bool:
        return bool(self._t and self._t.is_alive())

    def tick_once(self, k: int) -> None:
        """One 250 ms frame. k = frame number."""
        r = self.rng
        for m, (_, vol) in MARKETS.items():
            self.px[m] *= 1 + self.g() * vol * .35
            p = self.px[m]
            _emit("tick", {"market": m, "price": p, "bid": p * (1 - .00004), "ask": p * (1 + .00004)})
            if m == "XAU/USD" and r.random() < .35:
                _emit("orderflow_bubble", {"market": m, "price": p, "size": math.exp(self.g() * .8) * 40, "side": "buy" if r.random() < .5 else "sell"})
        if k % 6 == 0:
            x, t = r.random(), r.choice(TITLES)
            if x < .2:
                _emit("ticker_log", {"verb": "SEARCH", "msg": f"{r.choice(SEARCHES)} · {3 + r.randrange(9)} results, {r.randrange(3)} new"})
            elif x < .4:
                _emit("ticker_log", {"verb": "READ", "msg": f'Browser opens "{t}" · {1200 + r.randrange(2400)} words'})
            elif x < .55:
                _emit("ticker_log", {"verb": "SUMMARISE", "msg": f'"{t}" → idea type {r.choice(IDEA_TYPES)}'})
            elif x < .7:
                _emit("ticker_log", {"verb": "SAVE", "msg": f"source saved · {r.choice(IDEA_TYPES)} cluster"})
            else:
                _emit("ticker_log", {"verb": "TEST", "msg": f"{r.choice(RECIPES)} {8 + r.randrange(12)} · 4h · walk-forward started"})
        if k % 10 == 0:
            _emit("source_added", {"kind": r.choice(["YouTube", "GitHub", "arXiv", "Web"]), "title": r.choice(TITLES), "idea": r.choice(IDEA_TYPES)})
            a, b = r.choice(AGENTS[1:10]), r.choice(AGENTS[1:10])
            if a != b:
                _emit("agent_handoff", {"from": a, "to": b, "item": r.choice(TITLES)})
        if k % 9 == 0:
            self.tested += 1
            is_s = self.g() * .5 + .4
            oos = is_s - abs(self.g()) * .9 + self.g() * .15
            out = "clear" if oos >= 1.4 else "sieve" if oos > .7 and r.random() < .5 else "failed"
            _emit("variant_tested", {"id": self.tested, "recipe": f"{r.choice(RECIPES)} {1 + r.randrange(20)}",
                                     "market": r.choice(["XAU", "BTC", "ETH", "NVDA"]), "tf": r.choice(["5m", "15m", "1h", "4h"]),
                                     "sharpeIS": round(is_s, 2), "sharpeOOS": round(oos, 2), "trades": 40 + r.randrange(600),
                                     "win": round(38 + r.random() * 24, 1), "rr": round(1 + r.random() * 1.4, 2),
                                     "dd": round(-4 - r.random() * 22, 1), "outcome": out, "why": r.choice(FAILS) if out == "failed" else None,
                                     "seed": r.randrange(10 ** 9)})
        if k % 20 == 0:
            _emit("budget_update", {"used": 31 + r.random() * .5, "of": 50, "days": 18})
        if k % 4 == 0:
            self._trade_card(k // 4)

    def _trade_card(self, s: int) -> None:
        """A demo trade card cycle, one step per second, 40 s per cycle."""
        i = s % 40
        p = self.px["XAU/USD"]
        pid = f"demo-{s // 40}"
        stop, target = round(p - 6, 2), round(p + 9.6, 2)
        seq = {0: ("scan_hit", {"plan_id": pid, "strategy": "OF-1-XAU", "market": "XAU/USD", "tf": "15m", "side": "buy", "reason": "sweep and reclaim", "scanned": 5900}),
               2: ("news_hit", {"plan_id": pid, "market": "XAU/USD", "blackout": False, "events": [], "window_min": 15}),
               4: ("forecast_done", {"plan_id": pid, "engine": "block-bootstrap fallback", "paths": 1000, "agree_pct": 61.2, "need_pct": 55, "passed": True}),
               6: ("entry_state", {"plan_id": pid, "state": "triggered", "market": "XAU/USD", "entry": p, "stop": stop, "target": target}),
               8: ("timemachine_done", {"plan_id": pid, "replays": 10000, "p_target": 29.4, "p_stop": 25.5, "p_open": 45.1, "passed": True}),
               10: ("size_calc", {"plan_id": pid, "equity": 10000, "currency": "GBP", "qty": 0.21, "max_loss": 100.0}),
               11: ("risk_check", {"plan_id": pid, "market": "XAU/USD", "passed": True, "checks": [], "blocked_by": []}),
               13: ("order_sent", {"plan_id": pid, "market": "XAU/USD", "side": "buy", "qty": 0.21, "stop": stop, "target": target, "broker": "paper"}),
               14: ("order_filled", {"plan_id": pid, "market": "XAU/USD", "side": "buy", "qty": 0.21, "price": p, "broker": "paper"}),
               24: ("position_update", {"plan_id": pid, "market": "XAU/USD", "event": "scale_out", "closed_qty": 0.1, "r": 1.0}),
               36: ("exit_done", {"plan_id": pid, "market": "XAU/USD", "side": "buy", "pnl": 168.0, "r": 1.3, "reason": "target"})}
        if i in seq:
            _emit(*seq[i])
        if 8 > i >= 6:
            _emit("timemachine_progress", {"plan_id": pid, "done": (i - 5) * 5000, "of": 10000})

    def _run(self) -> None:
        k = 0
        nxt = time.monotonic()
        while not self._stop.is_set():
            self.tick_once(k)
            k += 1
            nxt += 0.25
            self._stop.wait(max(0.0, nxt - time.monotonic()))


source = DemoSource()
