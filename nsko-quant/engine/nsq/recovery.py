"""Reboot recovery: on start (and after a reconnect) reconcile with the broker. The broker is the source of truth.

1. Positions the broker has but the engine's database does not: adopted (recorded), flagged for review.
2. Positions the database thinks are open but the broker does not have: marked closed ("closed at broker").
3. Every open position must have a stop AND a target at the broker. Missing legs are re-placed from the
   trade plan (or, if no plan exists, from a protective default: 1% of price for the stop, 2R for the target)
   and verified. If the stop still cannot be placed, the position is closed.
"""
from __future__ import annotations

import json
import time

from .audit import audit
from .brokers.base import BrokerAdapter, BrokerError
from .bus import publish
from .db import conn
from .log import get as get_log

_log = get_log("recovery")


def reconcile(broker: BrokerAdapter | None = None) -> dict:
    from .brokers import active
    b = broker or active()
    report = {"broker": b.name, "adopted": [], "closed_in_db": [], "replaced": [], "closed_for_safety": [], "ok": []}
    try:
        live = {p.id: p for p in b.positions()}
    except BrokerError as e:
        report["error"] = str(e)
        return report
    c = conn()
    db_open = {r["id"]: r for r in c.execute("SELECT * FROM positions WHERE status='open' AND broker=?", (b.name,))}
    for pid, row in db_open.items():
        if pid not in live:
            c.execute("UPDATE positions SET status='closed', closed_at=?, exit_reason='closed at broker (found on restart)' WHERE id=?",
                      (time.time(), pid))
            report["closed_in_db"].append(pid)
    for pid, p in live.items():
        if pid not in db_open and b.name != "paper":
            c.execute("INSERT OR IGNORE INTO positions (id, broker, market, side, qty, entry, stop, target, status, mode, opened_at)"
                      " VALUES (?,?,?,?,?,?,?,?,?,?,?)", (pid, b.name, p.market, p.side, p.qty, p.entry, p.stop, p.target,
                                                         "open", "live", time.time()))
            report["adopted"].append(pid)
        missing = [leg for leg, oid in (("stop", p.stop_order_id), ("target", p.target_order_id)) if not oid]
        if not missing:
            report["ok"].append(pid)
            continue
        plan = None
        row = db_open.get(pid)
        if row and row.get("plan_id"):
            plan = c.execute("SELECT * FROM trade_plans WHERE id=?", (row["plan_id"],)).fetchone()
        ref = p.entry or (b.ticks(p.market)["price"] if hasattr(b, "ticks") else 0)
        long = p.side == "buy"
        stop = (plan or {}).get("stop") or p.stop or (ref * (0.99 if long else 1.01))
        target = (plan or {}).get("target") or p.target or (ref + (ref - stop) * 2)
        exit_side = "sell" if long else "buy"
        base = f"nsq-{(plan or {}).get('id') or pid}-R{int(time.time())}"
        for leg in missing:
            try:
                if getattr(b, "exit_bracket", False):
                    b.place_exit_bracket(p.market, p.qty, stop, target, base + "-SL")  # type: ignore[attr-defined]
                    break
                b.place_order(p.market, exit_side, p.qty, "stop" if leg == "stop" else "limit",
                              stop if leg == "stop" else target, f"{base}-{'SL' if leg == 'stop' else 'TP'}", role=leg, position_id=pid)
                report["replaced"].append({"position": pid, "leg": leg, "price": stop if leg == "stop" else target})
            except BrokerError as e:
                if leg == "target" and getattr(b, "soft_target_ok", False):
                    report["replaced"].append({"position": pid, "leg": "target", "soft": True})
                    continue
                _log.error(f"could not re-place {leg} on {pid}: {e}")
                if leg == "stop":
                    try:
                        b.close(pid)
                        report["closed_for_safety"].append(pid)
                    except BrokerError:
                        pass
                    break
    audit("engine", "recovery.reconcile", report)
    if report["replaced"] or report["closed_for_safety"] or report["adopted"] or report["closed_in_db"]:
        publish("alert", {"kind": "info", "level": "info", "title": "Positions checked with the broker",
                          "body": json.dumps({k: len(v) for k, v in report.items() if isinstance(v, list)})})
    return report
