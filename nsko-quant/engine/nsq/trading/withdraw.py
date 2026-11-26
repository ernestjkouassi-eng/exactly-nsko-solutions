"""Withdraw helper (9.7). Information only: it computes how much is free and links to the broker's own
withdrawal page. There is NO money-moving code anywhere in this engine. You withdraw yourself, on the
broker's website, with your own login and 2FA.

Steps the desk walks through: pause new trades -> (optionally) close positions -> withdraw at the broker ->
rescale (sizes always come from the live equity) and resume.
"""
from __future__ import annotations

from ..audit import audit
from ..settings import get, set as sset


def helper(broker=None) -> dict:
    from ..brokers import active
    b = broker or active()
    a = b.account()
    free = max(0.0, a.equity - a.margin_used)
    pos = b.positions()
    open_n = len(pos)
    return {"broker": b.name, "currency": a.currency, "equity": a.equity, "margin_used": a.margin_used,
            "free_to_withdraw": round(free, 2), "open_positions": open_n,
            "positions": [{"id": p.id, "market": p.market, "side": p.side.upper(), "qty": p.qty,
                           "pnl": round(float(getattr(p, "unrealised", 0.0) or 0.0), 2)} for p in pos],
            "trading_paused": bool(get("trading.paused", False)),
            "withdraw_url": b.withdraw_url() or None, "paper": b.name == "paper",
            "note": ("Paper money: nothing to withdraw." if b.name == "paper" else
                     "Open the broker's page and withdraw there yourself. NSKO QUANT cannot move money."
                     + (" Closing open positions first frees the margin they use." if open_n else ""))}


def set_paused(paused: bool, actor: str = "user", why: str = "") -> dict:
    sset("trading.paused", bool(paused))
    audit(actor, "trading.paused" if paused else "trading.resumed", {"why": why} if why else {})
    from ..bus import publish
    publish("ticker_log", {"verb": "PAUSE" if paused else "TRADE",
                           "msg": "new trades paused" + (f" · {why}" if why else "") if paused else "new trades resumed"})
    return {"trading_paused": bool(paused)}


def action(name: str, actor: str = "user", broker=None) -> dict:
    """One step of the withdraw helper: pause | close_positions | rescale | resume."""
    from ..brokers import active
    b = broker or active()
    if name == "pause":
        return {"ok": True, **set_paused(True, actor, "withdraw helper")}
    if name == "resume":
        return {"ok": True, **set_paused(False, actor, "withdraw helper")}
    if name == "close_positions":
        if not get("trading.paused", False):
            return {"ok": False, "message": "Pause new trades first."}
        closed, errors = 0, []
        for p in b.positions():
            try:
                b.close(p.id, reason="withdraw") if hasattr(b, "set_price") else b.close(p.id)
                closed += 1
            except Exception as e:   # report, never hide a position that is still open
                errors.append(f"{p.market}: {e}")
        audit(actor, "withdraw.close_positions", {"closed": closed, "errors": errors})
        return {"ok": not errors, "closed": closed, "errors": errors, **helper(b)}
    if name == "rescale":
        a = b.account()
        audit(actor, "withdraw.rescale", {"equity": a.equity})
        return {"ok": True, "new_equity": a.equity, "currency": a.currency,
                "message": f"Every new trade is sized from the new balance ({a.equity:,.2f} {a.currency})."}
    raise ValueError("action is pause, close_positions, rescale or resume")
