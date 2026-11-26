"""Withdraw helper (9.7). Information only: it computes how much is free and links to the broker's own
withdrawal page. There is NO money-moving code anywhere in this engine. You withdraw yourself, on the
broker's website, with your own login and 2FA."""
from __future__ import annotations


def helper(broker=None) -> dict:
    from ..brokers import active
    b = broker or active()
    a = b.account()
    free = max(0.0, a.equity - a.margin_used)
    open_n = len(b.positions())
    return {"broker": b.name, "currency": a.currency, "equity": a.equity, "margin_used": a.margin_used,
            "free_to_withdraw": round(free, 2), "open_positions": open_n,
            "withdraw_url": b.withdraw_url() or None, "paper": b.name == "paper",
            "note": ("Paper money: nothing to withdraw." if b.name == "paper" else
                     "Open the broker's page and withdraw there yourself. NSKO QUANT cannot move money."
                     + (" Closing open positions first frees the margin they use." if open_n else ""))}
