"""Kill switch: cancel all orders, close all positions, lock trading until re-enabled.

Reachable from POST /kill and the Telegram `/kill` command (paired chat id only).
"""
from __future__ import annotations

import datetime as dt

from ..audit import audit
from ..bus import publish
from ..settings import get, set


def is_locked() -> tuple[bool, str | None]:
    if get("trading.locked", False):
        return True, f"kill switch on ({get('trading.lock_reason', 'kill switch')}). Re-enable trading to continue."
    day = get("trading.day_stop", None)
    if day and day == dt.datetime.now(dt.timezone.utc).date().isoformat():
        return True, "daily loss limit reached: trading stopped for today"
    return False, None


def kill(source: str = "api", reason: str = "kill switch pressed", broker=None) -> dict:
    from ..brokers import active
    b = broker or active()
    set("trading.locked", True)
    set("trading.lock_reason", reason)
    cancelled, closed, errors = 0, 0, []
    try:
        for o in b.orders():
            try:
                if b.cancel(o.id):
                    cancelled += 1
            except Exception as e:
                errors.append(f"cancel {o.id}: {e}")
        for p in b.positions():
            try:
                b.close(p.id) if not hasattr(b, "set_price") else b.close(p.id, reason="kill")
                closed += 1
            except Exception as e:
                errors.append(f"close {p.id}: {e}")
    except Exception as e:
        errors.append(str(e))
    from ..db import conn
    conn().execute("UPDATE trade_plans SET state='killed' WHERE state IN ('awaiting_approval','sizing','pending')")
    res = {"locked": True, "cancelled": cancelled, "closed": closed, "errors": errors, "source": source}
    audit(source, "kill_switch", res | {"reason": reason})
    publish("kill_switch", {"on": True, **res, "reason": reason})
    from ..notify import notify
    notify("kill", "KILL SWITCH ON", f"{reason}. Cancelled {cancelled} orders, closed {closed} positions. Trading locked.",
           level="critical")
    return res


def enable(actor: str = "user") -> dict:
    set("trading.locked", False)
    set("trading.lock_reason", None)
    audit(actor, "trading_enabled", {})
    publish("kill_switch", {"on": False})
    return {"locked": False}
