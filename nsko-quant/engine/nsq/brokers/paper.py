"""PaperBroker: the default broker. A local simulator with realistic costs.

- Fills: market orders fill at the ask (buy) / bid (sell) plus adverse slippage; stops fill at the stop
  (or the worse bar price on a gap) minus slippage; targets (limits) fill at the limit, never better.
- Spread, slippage and commission per market from `MarketSpec` (brokers/base.py).
- Native bracket orders (entry + stop + target, one-cancels-other) and partial closes.
- Idempotent: the same client_order_id never opens a second position.
- State is written to the orders / positions / fills tables (broker='paper'), so a restart picks up
  where it left off, exactly as a real broker would after a reboot.
- `native_brackets=False` and `fail_roles` let tests exercise the no-native-bracket fallback path.
Account currency is GBP. Every number this broker produces is PAPER money.
"""
from __future__ import annotations

import math
import random
import threading
import time
import uuid
from typing import Any, Callable

from ..db import conn
from .base import (Account, BracketResult, BrokerAdapter, BrokerError, Order, Position, fx_to_account, spec,
                   value_per_point, MARKETS)


def _id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:10]}"


class PaperBroker(BrokerAdapter):
    name = "paper"
    title = "Paper trading (simulator)"
    status = "ready"
    native_brackets = True
    markets = tuple(MARKETS)
    withdraw_page = ""

    def __init__(self, start_balance: float | None = None, seed: int = 20261126, persist: bool = True,
                 native_brackets: bool = True):
        self._lock = threading.RLock()
        self.rng = random.Random(seed)
        self.persist = persist
        self.native_brackets = native_brackets
        self.fail_roles: set[str] = set()     # tests: roles whose placement fails ("stop", "target", "close")
        self.connected = True                # tests: False simulates the internet dropping
        self.quotes: dict[str, dict] = {}
        self._orders: dict[str, Order] = {}
        self._cid: dict[str, str] = {}       # client_order_id -> order id
        self._positions: dict[str, Position] = {}
        self._listeners: list[Callable[[dict], None]] = []
        self.balance = float(start_balance if start_balance is not None else self._setting("paper.start_balance", 10000.0))
        if persist:
            self._load()

    # ------------------------------------------------------------------ persistence
    def _setting(self, k: str, d: Any) -> Any:
        try:
            from ..settings import get
            return get(k, d)
        except Exception:
            return d

    def _load(self) -> None:
        from ..settings import get
        self.balance = float(get("paper.balance", self.balance))
        c = conn()
        for r in c.execute("SELECT * FROM positions WHERE broker='paper' AND status='open'"):
            self._positions[r["id"]] = Position(r["id"], r["market"], r["side"], r["qty"], r["entry"], r["stop"], r["target"],
                                                realised=r["realised"], opened_at=r["opened_at"],
                                                meta={"plan_id": r["plan_id"], "strategy_id": r["strategy_id"]})
        for r in c.execute("SELECT * FROM orders WHERE broker='paper'"):
            role = "entry"
            cid = r["client_order_id"]
            role = "stop" if cid.endswith("-SL") else "target" if cid.endswith("-TP") else "exit" if "-X" in cid else "entry"
            o = Order(r["id"], cid, r["market"], r["side"], r["kind"], r["qty"], r["price"], r["status"], role,
                      r["parent_id"], r["plan_id"])
            self._orders[o.id] = o
            self._cid[cid] = o.id
            if o.status == "open" and o.position_id in self._positions:
                p = self._positions[o.position_id]
                if role == "stop":
                    p.stop_order_id = o.id
                elif role == "target":
                    p.target_order_id = o.id

    def _save_order(self, o: Order) -> None:
        if not self.persist:
            return
        now = time.time()
        conn().execute(
            "INSERT INTO orders (id, client_order_id, broker, plan_id, market, side, kind, qty, price, status, parent_id, created_at, updated_at)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET qty=excluded.qty, price=excluded.price,"
            " status=excluded.status, plan_id=excluded.plan_id, updated_at=excluded.updated_at",
            (o.id, o.client_order_id, "paper", o.position_id, o.market, o.side, o.kind, o.qty, o.price, o.status, o.parent_id, now, now))

    def _save_position(self, p: Position, status: str = "open", exit_price: float | None = None, reason: str | None = None) -> None:
        if not self.persist:
            return
        c = conn()
        c.execute(
            "INSERT INTO positions (id, broker, plan_id, strategy_id, market, side, qty, entry, stop, target, initial_qty, initial_stop,"
            " realised, status, mode, opened_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)"
            " ON CONFLICT(id) DO UPDATE SET qty=excluded.qty, stop=excluded.stop, target=excluded.target,"
            " realised=excluded.realised, status=excluded.status",
            (p.id, "paper", p.meta.get("plan_id"), p.meta.get("strategy_id"), p.market, p.side, p.qty, p.entry, p.stop, p.target,
             p.meta.get("initial_qty", p.qty), p.meta.get("initial_stop", p.stop), p.realised, status, "paper", p.opened_at))
        if status == "closed":
            c.execute("UPDATE positions SET closed_at=?, exit_price=?, exit_reason=? WHERE id=?", (time.time(), exit_price, reason, p.id))
        from ..settings import set as sset
        sset("paper.balance", self.balance)

    def _save_fill(self, order: Order, qty: float, price: float, commission: float) -> None:
        if self.persist:
            conn().execute("INSERT INTO fills (order_id, broker, market, side, qty, price, commission, ts) VALUES (?,?,?,?,?,?,?,?)",
                           (order.id, "paper", order.market, order.side, qty, price, commission, time.time()))

    # ------------------------------------------------------------------ quotes
    def set_price(self, market: str, price: float, ts: float | None = None, high: float | None = None,
                  low: float | None = None) -> list[dict]:
        """Feed a new mid price (or a bar's high/low/close). Triggers resting stops and targets."""
        s = spec(market)
        half = s.spread / 2
        with self._lock:
            self.quotes[market] = {"market": market, "price": price, "bid": price - half, "ask": price + half,
                                   "ts": ts or time.time()}
            return self._trigger(market, high if high is not None else price, low if low is not None else price, price)

    def ticks(self, market: str) -> dict:
        q = self.quotes.get(market)
        if not q:
            raise BrokerError(f"no price yet for {market}")
        return dict(q)

    def stream(self, markets, on_event):
        self._listeners.append(on_event)
        return lambda: self._listeners.remove(on_event) if on_event in self._listeners else None

    def _emit(self, ev: dict) -> None:
        for fn in list(self._listeners):
            try:
                fn(ev)
            except Exception:
                pass

    def _slip(self, market: str) -> float:
        return abs(self.rng.gauss(0, 1)) * spec(market).slippage

    def _commission(self, market: str, qty: float, price: float) -> float:
        s = spec(market)
        return s.commission_per_qty * qty + s.commission_pct / 100 * price * qty * s.contract_size * fx_to_account(s.quote_ccy)

    # ------------------------------------------------------------------ BrokerAdapter
    def connect(self) -> bool:
        self.connected = True
        return True

    def online(self) -> bool:
        return self.connected

    def _require_online(self) -> None:
        if not self.connected:
            raise BrokerError("paper broker offline (simulated internet drop)")

    def _unrealised(self, p: Position) -> float:
        q = self.quotes.get(p.market)
        if not q:
            return 0.0
        mark = q["bid"] if p.side == "buy" else q["ask"]
        d = 1 if p.side == "buy" else -1
        return (mark - p.entry) * d * p.qty * value_per_point(p.market)

    def account(self) -> Account:
        with self._lock:
            unreal = sum(self._unrealised(p) for p in self._positions.values())
            margin = sum(p.qty * p.entry * spec(p.market).contract_size * fx_to_account(spec(p.market).quote_ccy) * 0.05
                         for p in self._positions.values())
            return Account("paper", "GBP", round(self.balance, 2), round(self.balance + unreal, 2), round(margin, 2), paper=True)

    def positions(self) -> list[Position]:
        with self._lock:
            out = []
            for p in self._positions.values():
                p.unrealised = round(self._unrealised(p), 2)
                out.append(Position(**{**p.__dict__, "meta": dict(p.meta)}))
            return out

    def orders(self) -> list[Order]:
        with self._lock:
            return [Order(**o.__dict__) for o in self._orders.values() if o.status == "open"]

    def all_orders(self) -> list[Order]:
        with self._lock:
            return [Order(**o.__dict__) for o in self._orders.values()]

    def _fill_market(self, market: str, side: str) -> float:
        q = self.quotes.get(market)
        if not q:
            raise BrokerError(f"no price for {market}: feed one with set_price() first")
        slip = self._slip(market)
        px = q["ask"] + slip if side == "buy" else q["bid"] - slip
        return round(px, 8)

    def place_bracket(self, market, side, qty, stop, target, client_order_id, meta: dict | None = None) -> BracketResult:
        with self._lock:
            if client_order_id in self._cid:     # idempotent replay
                o = self._orders[self._cid[client_order_id]]
                p = self._positions.get(o.position_id) if o.position_id else None
                so = self._orders.get(p.stop_order_id) if p and p.stop_order_id else None
                to = self._orders.get(p.target_order_id) if p and p.target_order_id else None
                return BracketResult(True, p, o, so, to, o.price, 0.0, idempotent_replay=True)
            self._require_online()
            if qty <= 0:
                raise BrokerError("size must be positive")
            if side == "buy" and not (stop < self._mid(market) < target) or side == "sell" and not (target < self._mid(market) < stop):
                raise BrokerError("stop and target must be either side of the price")
            px = self._fill_market(market, side)
            entry = self._open(market, side, qty, px, client_order_id, meta)
            p = self._positions[entry.position_id]
            if not self.native_brackets:
                return BracketResult(True, p, entry, None, None, px, p.meta["commission"])
            so = self._rest(p, "stop", stop, client_order_id + "-SL")
            to = self._rest(p, "target", target, client_order_id + "-TP")
            self._save_position(p)
            return BracketResult(True, Position(**{**p.__dict__, "meta": dict(p.meta)}), entry, so, to, px, p.meta["commission"])

    def _mid(self, market: str) -> float:
        q = self.quotes.get(market)
        if not q:
            raise BrokerError(f"no price for {market}")
        return q["price"]

    def _open(self, market, side, qty, px, cid, meta) -> Order:
        comm = self._commission(market, qty, px)
        pid = _id("pos")
        o = Order(_id("ord"), cid, market, side, "market", qty, px, "filled", "entry", None, pid)
        self._orders[o.id] = o
        self._cid[cid] = o.id
        self.balance -= comm
        p = Position(pid, market, side, qty, px, opened_at=time.time(),
                     meta={**(meta or {}), "commission": comm, "initial_qty": qty})
        self._positions[pid] = p
        self._save_order(o)
        self._save_fill(o, qty, px, comm)
        self._save_position(p)
        self._emit({"kind": "fill", "order": o.dict()})
        return o

    def _rest(self, p: Position, role: str, price: float, cid: str) -> Order:
        if role in self.fail_roles:
            raise BrokerError(f"simulated rejection of the {role} order")
        if cid in self._cid:                                  # idempotent retry of the same leg
            o = self._orders[self._cid[cid]]
            if o.status == "open":
                return o
        exit_side = "sell" if p.side == "buy" else "buy"
        o = Order(_id("ord"), cid, p.market, exit_side, "stop" if role == "stop" else "limit", p.qty, price, "open",
                  role, self._cid.get(cid.rsplit("-", 1)[0]), p.id)
        self._orders[o.id] = o
        self._cid[cid] = o.id
        if role == "stop":
            p.stop, p.stop_order_id = price, o.id
            p.meta.setdefault("initial_stop", price)
        else:
            p.target, p.target_order_id = price, o.id
        self._save_order(o)
        self._save_position(p)
        return o

    def place_order(self, market, side, qty, kind, price, client_order_id, role="entry", position_id=None) -> Order:
        """Used by the fallback path: an entry market order, or a stop / target attached to a position."""
        with self._lock:
            if client_order_id in self._cid and self._orders[self._cid[client_order_id]].status in ("open", "filled"):
                return Order(**self._orders[self._cid[client_order_id]].__dict__)
            self._require_online()
            if role == "entry":
                return self._open(market, side, qty, self._fill_market(market, side), client_order_id, None)
            p = self._positions.get(position_id or "")
            if not p:
                raise BrokerError("position not found")
            return Order(**self._rest(p, role, price, client_order_id).__dict__)

    def modify(self, order_id: str, price: float) -> Order:
        with self._lock:
            self._require_online()
            o = self._orders.get(order_id)
            if not o or o.status != "open":
                raise BrokerError("order not open")
            o.price = price
            p = self._positions.get(o.position_id or "")
            if p:
                if o.role == "stop":
                    p.stop = price
                elif o.role == "target":
                    p.target = price
                self._save_position(p)
            self._save_order(o)
            return Order(**o.__dict__)

    def cancel(self, order_id: str) -> bool:
        with self._lock:
            o = self._orders.get(order_id)
            if not o or o.status != "open":
                return False
            o.status = "cancelled"
            p = self._positions.get(o.position_id or "")
            if p:
                if p.stop_order_id == o.id:
                    p.stop_order_id, p.stop = None, None
                if p.target_order_id == o.id:
                    p.target_order_id, p.target = None, None
                self._save_position(p)
            self._save_order(o)
            return True

    def close(self, position_id: str, qty: float | None = None, reason: str = "manual", price: float | None = None) -> dict:
        """Close all or part of a position at market (or at `price` when a resting order triggered)."""
        with self._lock:
            if "close" in self.fail_roles:
                raise BrokerError("simulated rejection of the close")
            p = self._positions.get(position_id)
            if not p:
                raise BrokerError("position not found")
            qty = p.qty if qty is None or qty >= p.qty - 1e-12 else qty
            exit_side = "sell" if p.side == "buy" else "buy"
            px = price if price is not None else self._fill_market(p.market, exit_side)
            d = 1 if p.side == "buy" else -1
            comm = self._commission(p.market, qty, px)
            pnl = (px - p.entry) * d * qty * value_per_point(p.market) - comm
            self.balance += pnl
            p.realised += pnl
            xo = Order(_id("ord"), f"{position_id}-X{len(self._orders)}", p.market, exit_side, "market", qty, px, "filled", "exit",
                       None, p.id)
            self._orders[xo.id] = xo
            self._cid[xo.client_order_id] = xo.id
            self._save_order(xo)
            self._save_fill(xo, qty, px, comm)
            p.qty = round(p.qty - qty, 10)
            full = p.qty <= 1e-12
            for oid in (p.stop_order_id, p.target_order_id):
                o = self._orders.get(oid or "")
                if o and o.status == "open":
                    if full:
                        o.status = "cancelled"
                    else:
                        o.qty = p.qty
                    self._save_order(o)
            if full:
                self._positions.pop(p.id, None)
                self._save_position(p, "closed", px, reason)
            else:
                self._save_position(p)
            res = {"position_id": p.id, "closed_qty": qty, "remaining_qty": max(p.qty, 0.0), "price": px,
                   "pnl": round(pnl, 2), "commission": round(comm, 2), "full": full, "reason": reason,
                   "realised_total": round(p.realised, 2)}
            self._emit({"kind": "close", **res})
            return res

    def _trigger(self, market: str, high: float, low: float, last: float) -> list[dict]:
        """Check resting stops/targets against the new price range. Stop wins when both are touched
        inside one bar (the conservative assumption)."""
        events = []
        s = spec(market)
        half = s.spread / 2
        for p in list(self._positions.values()):
            if p.market != market:
                continue
            so = self._orders.get(p.stop_order_id or "")
            to = self._orders.get(p.target_order_id or "")
            # longs exit on the bid, shorts on the ask
            hi_exec, lo_exec = (high - half, low - half) if p.side == "buy" else (high + half, low + half)
            stop_hit = so and so.status == "open" and (lo_exec <= so.price if p.side == "buy" else hi_exec >= so.price)
            tgt_hit = to and to.status == "open" and (hi_exec >= to.price if p.side == "buy" else lo_exec <= to.price)
            if stop_hit:
                slip = self._slip(market)
                gap_px = min(so.price, last - half) if p.side == "buy" else max(so.price, last + half)
                px = (gap_px - slip) if p.side == "buy" else (gap_px + slip)
                so.status = "filled"
                self._save_order(so)
                events.append(self.close(p.id, reason="stop", price=round(px, 8)))
            elif tgt_hit:
                to.status = "filled"
                self._save_order(to)
                events.append(self.close(p.id, reason="target", price=to.price))
        return events

    # ------------------------------------------------------------------ data
    def candles(self, market: str, timeframe: str = "15m", start=None, end=None):
        try:
            from ..data import candles as data_candles  # other agent's module (lazy)
            return data_candles.get(market, timeframe, start, end)
        except Exception:
            from ..trading.synthetic import synthetic_candles
            return synthetic_candles(market, timeframe, n=500)

    def permissions(self) -> dict:
        return {"trading": True, "withdrawals": False, "detectable": True,
                "note": "Paper money only. Nothing can be withdrawn."}

    def reset(self, balance: float = 10000.0) -> None:
        with self._lock:
            self._positions.clear()
            self._orders.clear()
            self._cid.clear()
            self.balance = balance
