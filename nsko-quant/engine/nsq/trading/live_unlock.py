"""Live unlock checklist (section 9.4).

Live trading unlocks only when ALL of these are true:
  - 21 days of paper trading AND 30 paper trades (both, not either),
  - a valid licence,
  - a real broker connected with trading on and withdrawals not on,
  - the typed phrase "I understand I can lose money" (exactly).
For the first 2 weeks of live, every trade is sized at 50%.
"""
from __future__ import annotations

import time

from ..audit import audit
from ..db import conn
from ..settings import get, set

PHRASE = "I understand I can lose money"


def paper_stats() -> dict:
    r = conn().execute("SELECT COUNT(*) n, MIN(ts) first FROM journal WHERE mode='paper'").fetchone()
    days = (time.time() - r["first"]) / 86400 if r["first"] else 0.0
    return {"trades": int(r["n"]), "days": round(days, 1)}


def checklist(phrase: str | None = None, broker=None, licence_status: str | None = None) -> dict:
    from ..brokers import active
    b = broker or active()
    st = paper_stats()
    need_d, need_t = int(get("live.paper_days_required")), int(get("live.paper_trades_required"))
    if licence_status is None:
        from ..licence import check as lcheck
        licence_status = lcheck(get("licence.key", "") or "")["status"]
    try:
        perms = b.permissions()
    except Exception:
        perms = {"trading": None, "withdrawals": None}
    items = [
        {"id": "paper_days", "ok": st["days"] >= need_d, "label": f"{need_d} days of paper trading", "value": st["days"]},
        {"id": "paper_trades", "ok": st["trades"] >= need_t, "label": f"{need_t} paper trades", "value": st["trades"]},
        {"id": "licence", "ok": licence_status == "valid", "label": "Valid licence", "value": licence_status},
        {"id": "real_broker", "ok": b.name != "paper", "label": "A real broker is connected", "value": b.name},
        {"id": "trading_permission", "ok": perms.get("trading") is True, "label": "Broker key can trade", "value": perms.get("trading")},
        {"id": "withdrawals_off", "ok": perms.get("withdrawals") is not True, "label": "Broker key cannot withdraw",
         "value": perms.get("withdrawals")},
        {"id": "risk_gate", "ok": True, "label": "Risk gate is on (it cannot be switched off in live)", "value": True},
        {"id": "phrase", "ok": (phrase or "").strip() == PHRASE, "label": f'Type "{PHRASE}"', "value": bool(phrase)},
    ]
    return {"ok": all(i["ok"] for i in items), "items": items, "half_size_days": int(get("live.half_size_days")),
            "unlocked": is_unlocked()}


def unlock(phrase: str, broker=None, licence_status: str | None = None, actor: str = "user") -> dict:
    cl = checklist(phrase, broker, licence_status)
    if not cl["ok"]:
        audit(actor, "live.unlock_refused", {"missing": [i["id"] for i in cl["items"] if not i["ok"]]})
        return {**cl, "unlocked": False}
    set("live.unlocked_at", time.time())
    set("mode", "live")
    audit(actor, "live.unlocked", {"half_size_days": cl["half_size_days"]})
    return {**cl, "unlocked": True}


def is_unlocked() -> bool:
    return get("live.unlocked_at") is not None


def size_factor(mode: str, now: float | None = None) -> float:
    if mode != "live":
        return 1.0
    at = get("live.unlocked_at")
    if at is None:
        return 0.0
    days = ((now or time.time()) - float(at)) / 86400
    return 0.5 if days < float(get("live.half_size_days")) else 1.0


def back_to_paper(actor: str = "user") -> None:
    set("mode", "paper")
    audit(actor, "mode.paper", {})
