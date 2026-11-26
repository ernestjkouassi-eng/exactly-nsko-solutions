"""Execute a bracket order, with a verified fallback for brokers that have no native brackets.

Native:   place_bracket(...) -> verify the stop and target exist at the broker -> re-place any missing leg.
Fallback: market entry -> place stop -> place target -> verify both exist.
          (Coinbase: one OCO exit bracket holds both legs.)
          (Kraken: if the broker refuses the second exit order for lack of free balance, the stop stays
           broker-side and the target is watched by the engine: `soft_target`.)
If the stop cannot be placed and verified after retries, the position is CLOSED at once.
Retries reuse the same client order IDs, so a retry never opens a second position or a duplicate leg.
"""
from __future__ import annotations

import time

from ..audit import audit
from ..brokers.base import BrokerAdapter, BrokerError
from ..bus import publish

RETRIES = 3


def client_ids(plan_id: str) -> dict:
    base = f"nsq-{plan_id}"
    return {"entry": base, "stop": base + "-SL", "target": base + "-TP"}


def _legs_present(broker: BrokerAdapter, position_id: str | None, market: str) -> tuple[bool, bool]:
    stop = target = False
    for p in broker.positions():
        if (position_id and p.id == position_id) or (not position_id and p.market == market):
            stop, target = p.stop_order_id is not None, p.target_order_id is not None
    open_ids = {o.id for o in broker.orders()}
    for p in broker.positions():
        if position_id and p.id == position_id:
            stop = stop and p.stop_order_id in open_ids
            target = target and p.target_order_id in open_ids
    return stop, target


def execute_bracket(broker: BrokerAdapter, plan: dict, sleep=time.sleep) -> dict:
    """plan: {id, market, side, qty, stop, target}. Returns a result dict; never leaves a naked position."""
    ids = client_ids(plan["id"])
    m, side, qty, stop, target = plan["market"], plan["side"], plan["qty"], plan["stop"], plan["target"]
    exit_side = "sell" if side == "buy" else "buy"
    publish("order_sent", {"plan_id": plan["id"], "market": m, "side": side, "qty": qty, "stop": stop, "target": target,
                           "client_order_id": ids["entry"], "broker": broker.name, "bracket": "native" if broker.native_brackets else "fallback"})
    res = {"ok": False, "path": "native" if broker.native_brackets else "fallback", "soft_target": False,
           "position_id": None, "fill_price": None, "retries": 0, "closed_for_safety": False}
    last_err = None
    # ---- entry (+ native legs) with idempotent retries
    for attempt in range(RETRIES):
        try:
            if broker.native_brackets:
                br = broker.place_bracket(m, side, qty, stop, target, ids["entry"])
                res.update(position_id=br.position.id if br.position else None, fill_price=br.fill_price)
            else:
                o = broker.place_order(m, side, qty, "market", None, ids["entry"], role="entry")
                pos = next((p for p in broker.positions() if p.market == m), None)
                res.update(position_id=o.position_id or (pos.id if pos else None), fill_price=o.price)
            last_err = None
            break
        except BrokerError as e:
            last_err = str(e)
            res["retries"] += 1
            sleep(0.2 * (attempt + 1))
    if last_err:
        res["error"] = f"entry failed: {last_err}"
        audit("engine", "order.entry_failed", {"plan_id": plan["id"], "error": last_err})
        return res
    publish("order_filled", {"plan_id": plan["id"], "market": m, "side": side, "qty": qty, "price": res["fill_price"],
                             "position_id": res["position_id"], "broker": broker.name})
    # ---- make sure both protective legs exist
    for attempt in range(RETRIES):
        has_stop, has_target = _legs_present(broker, res["position_id"], m)
        if has_stop and (has_target or res["soft_target"]):
            break
        try:
            if getattr(broker, "exit_bracket", False) and not has_stop:
                broker.place_exit_bracket(m, qty, stop, target, ids["stop"])          # type: ignore[attr-defined]
                continue
            if not has_stop:
                broker.place_order(m, exit_side, qty, "stop", stop, ids["stop"], role="stop", position_id=res["position_id"])
            if not has_target:
                try:
                    broker.place_order(m, exit_side, qty, "limit", target, ids["target"], role="target",
                                       position_id=res["position_id"])
                except BrokerError as e:
                    if getattr(broker, "soft_target_ok", False) and _legs_present(broker, res["position_id"], m)[0]:
                        res["soft_target"] = True
                    else:
                        raise e
        except BrokerError as e:
            last_err = str(e)
            res["retries"] += 1
            sleep(0.2 * (attempt + 1))
    has_stop, has_target = _legs_present(broker, res["position_id"], m)
    res["verified"] = {"stop": has_stop, "target": has_target or res["soft_target"]}
    if not (has_stop and (has_target or res["soft_target"])):
        # Never leave an unprotected position: close it now.
        try:
            if res["position_id"]:
                broker.close(res["position_id"])
            res["closed_for_safety"] = True
        except BrokerError as e:
            res["close_error"] = str(e)
        res["error"] = f"could not place and verify stop/target ({last_err}); position closed for safety"
        audit("engine", "order.unprotected_closed", {"plan_id": plan["id"], "error": last_err})
        from ..notify import notify
        notify("error", "Trade closed for safety", f"{m}: stop/target could not be placed. {last_err}", level="error")
        return res
    res["ok"] = True
    audit("engine", "order.bracket_placed", {"plan_id": plan["id"], "market": m, "side": side, "qty": qty,
                                              "stop": stop, "target": target, "path": res["path"],
                                              "soft_target": res["soft_target"], "client_order_id": ids["entry"]})
    return res
