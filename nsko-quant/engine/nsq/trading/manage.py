"""MANAGE and EXIT: scale out 50% at 1R and move the stop to breakeven, optional ATR trail, flatten at the
end of the session for intraday strategies, engine-side soft targets, then JOURNAL + ALERT on exit.
"""
from __future__ import annotations

import json
import threading
import time

from ..audit import audit
from ..brokers.base import BrokerAdapter, BrokerError, value_per_point
from ..bus import publish
from ..db import conn
from ..settings import get


class Manager:
    def __init__(self, broker: BrokerAdapter):
        self.broker = broker
        self.tracked: dict[str, dict] = {}
        self._lock = threading.RLock()

    def track(self, position_id: str, plan: dict, soft_target: bool = False, session_end: float | None = None) -> None:
        with self._lock:
            self.tracked[position_id] = {"plan": plan, "entry": plan.get("fill_price") or plan["entry"],
                                         "initial_stop": plan["stop"], "qty0": plan["qty"], "scaled": False,
                                         "soft_target": soft_target, "session_end": session_end,
                                         "intraday": plan.get("intraday", True), "realised": 0.0}

    def on_price(self, market: str, price: float, now: float | None = None, atr: float | None = None) -> list[dict]:
        """Call after every new price / closed bar for `market`."""
        now = now or time.time()
        out = []
        with self._lock:
            live = {p.id: p for p in self.broker.positions()}
            for pid, t in list(self.tracked.items()):
                plan = t["plan"]
                if plan["market"] != market:
                    continue
                p = live.get(pid)
                if p is None:
                    out.append(self._finish(pid, t, price, "broker exit (stop or target)"))
                    continue
                long = plan["side"] == "buy"
                r_dist = abs(t["entry"] - t["initial_stop"])
                move_r = ((price - t["entry"]) if long else (t["entry"] - price)) / r_dist if r_dist else 0.0
                # soft target (engine-side, Kraken)
                if t["soft_target"] and ((long and price >= plan["target"]) or (not long and price <= plan["target"])):
                    if p.stop_order_id:
                        self.broker.cancel(p.stop_order_id)
                    self._close(pid, None, "target (engine-side)")
                    out.append(self._finish(pid, t, price, "target"))
                    continue
                # end of session flatten
                if t["intraday"] and t["session_end"] and now >= t["session_end"]:
                    self._close(pid, None, "end of session")
                    out.append(self._finish(pid, t, price, "end of session"))
                    continue
                # scale out at 1R, stop to breakeven
                if not t["scaled"] and move_r >= float(get("manage.scale_out_r")):
                    part = self._scale_qty(plan["market"], p.qty)
                    if part > 0:
                        r = self._close(pid, part, "scale-out 1R")
                        t["realised"] += float(r.get("pnl", 0) or 0)
                    if p.stop_order_id:
                        try:
                            self.broker.modify(p.stop_order_id, t["entry"])
                        except BrokerError:
                            pass
                    t["scaled"] = True
                    audit("engine", "position.scale_out", {"position_id": pid, "qty": part, "stop": t["entry"]})
                    publish("position_update", {"position_id": pid, "plan_id": plan["id"], "market": market, "event": "scale_out",
                                                "closed_qty": part, "stop": t["entry"], "r": round(move_r, 2), "price": price})
                    continue
                # optional trail after scale-out
                if get("manage.trail") and t["scaled"] and atr and p.stop_order_id:
                    k = float(get("manage.trail_atr_mult"))
                    new = price - k * atr if long else price + k * atr
                    if (long and new > (p.stop or -1e18)) or (not long and new < (p.stop or 1e18)):
                        self.broker.modify(p.stop_order_id, new)
                        publish("position_update", {"position_id": pid, "plan_id": plan["id"], "market": market,
                                                    "event": "trail", "stop": new, "price": price})
                        continue
                publish("position_update", {"position_id": pid, "plan_id": plan["id"], "market": market, "event": "mark",
                                            "price": price, "r": round(move_r, 2), "unrealised": p.unrealised, "qty": p.qty})
        return [o for o in out if o]

    def _scale_qty(self, market: str, qty: float) -> float:
        from ..brokers.base import round_down, spec
        s = spec(market)
        part = round_down(qty * float(get("manage.scale_out_frac")), s.qty_step)
        return part if part >= s.min_qty and part < qty else 0.0

    def _close(self, pid: str, qty: float | None, reason: str) -> dict:
        try:
            if hasattr(self.broker, "set_price"):
                return self.broker.close(pid, qty, reason=reason)  # type: ignore[call-arg]
            return self.broker.close(pid, qty)
        except BrokerError as e:
            return {"error": str(e)}

    def flatten_all(self, reason: str = "end of session") -> None:
        with self._lock:
            for pid in list(self.tracked):
                self._close(pid, None, reason)

    def _finish(self, pid: str, t: dict, price: float, reason: str) -> dict | None:
        self.tracked.pop(pid, None)
        plan = t["plan"]
        row = conn().execute("SELECT realised, exit_price, exit_reason FROM positions WHERE id=?", (pid,)).fetchone()
        if row and row["exit_price"] is not None:
            pnl, exit_px, reason = float(row["realised"]), float(row["exit_price"]), row["exit_reason"] or reason
        else:
            d = 1 if plan["side"] == "buy" else -1
            exit_px = price
            pnl = t["realised"] + (price - t["entry"]) * d * (t["qty0"] if not t["scaled"] else t["qty0"] / 2) * value_per_point(plan["market"])
        risk_gbp = abs(t["entry"] - t["initial_stop"]) * t["qty0"] * value_per_point(plan["market"])
        r_mult = pnl / risk_gbp if risk_gbp else 0.0
        mode = plan.get("mode", "paper")
        conn().execute("INSERT INTO journal (ts, plan_id, position_id, market, side, pnl, r_multiple, mode, detail) VALUES (?,?,?,?,?,?,?,?,?)",
                       (time.time(), plan["id"], pid, plan["market"], plan["side"], pnl, r_mult, mode,
                        json.dumps({"reason": reason, "exit": exit_px, "entry": t["entry"], "scaled": t["scaled"]})))
        conn().execute("UPDATE trade_plans SET state='closed', updated_at=? WHERE id=?", (time.time(), plan["id"]))
        ev = {"plan_id": plan["id"], "position_id": pid, "market": plan["market"], "side": plan["side"], "exit": exit_px,
              "pnl": round(pnl, 2), "r": round(r_mult, 2), "reason": reason, "mode": mode, "demo": False}
        publish("exit_done", ev)
        audit("engine", "trade.exit", ev)
        from ..notify import notify
        notify("trade", f"{'PAPER' if mode == 'paper' else 'LIVE'} exit {plan['market']}",
               f"{plan['side'].upper()} closed ({reason}) · P&L £{pnl:,.2f} · {r_mult:+.2f}R")
        return ev
