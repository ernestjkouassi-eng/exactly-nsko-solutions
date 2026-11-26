"""Position sizing: max £ loss per trade ÷ (stop distance × value per point), rounded DOWN to the broker step."""
from __future__ import annotations

from ..brokers.base import round_down, spec, value_per_point


def size_trade(equity: float, risk_pct: float, entry: float, stop: float, market: str,
               size_factor: float = 1.0, qty_step: float | None = None, min_qty: float | None = None,
               vpp: float | None = None) -> dict:
    s = spec(market)
    step = qty_step if qty_step is not None else s.qty_step
    mn = min_qty if min_qty is not None else s.min_qty
    vpp = vpp if vpp is not None else value_per_point(market)
    stop_dist = abs(entry - stop)
    max_loss = equity * risk_pct / 100.0 * size_factor
    if stop_dist <= 0 or vpp <= 0:
        return {"qty": 0.0, "reason": "stop distance is zero", "max_loss": max_loss, "stop_dist": stop_dist}
    raw = max_loss / (stop_dist * vpp)
    qty = round_down(raw, step)
    reason = "ok"
    if qty < mn:
        qty, reason = 0.0, f"size {raw:.6f} is below the broker minimum {mn}"
    return {"qty": qty, "raw_qty": raw, "step": step, "min_qty": mn, "max_loss": round(max_loss, 2),
            "risk_at_stop": round(qty * stop_dist * vpp, 2), "stop_dist": stop_dist, "value_per_point": vpp,
            "size_factor": size_factor, "reason": reason}
