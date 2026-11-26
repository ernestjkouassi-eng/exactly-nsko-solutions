"""Time Machine: 10,000 block-bootstrap replays of the rest of the session from the market's own recent bars.

Outputs P(target first), P(stop first), P(still open at session end).
Rule: P(target)·reward − P(stop)·risk > 0 AFTER costs (spread + slippage both ways + commission, in points).
If stop and target are both touched inside the same simulated bar, the stop counts first (conservative).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from ..brokers.base import spec, value_per_point
from ..bus import publish
from ..settings import get
from .paths import bar_moves, bootstrap, price_paths


def cost_points(market: str, entry: float, qty: float = 1.0) -> float:
    s = spec(market)
    comm_pts = 0.0
    vpp = value_per_point(market)
    if vpp > 0:
        comm_gbp = 2 * (s.commission_per_qty + s.commission_pct / 100 * entry * vpp)
        comm_pts = comm_gbp / vpp
    return s.spread + 2 * s.slippage + comm_pts


def run(df: pd.DataFrame, side: str, entry: float, stop: float, target: float, bars_left: int,
        market: str = "", n: int | None = None, block: int | None = None, seed: int = 1, plan_id: str | None = None,
        emit: bool = True) -> dict:
    n = int(n or get("timemachine.replays"))
    block = int(block or get("timemachine.block"))
    bars_left = max(1, int(bars_left))
    moves = bar_moves(df.tail(500))
    hit_t = np.zeros(n, dtype=bool)
    hit_s = np.zeros(n, dtype=bool)
    chunk = max(1, n // 5)
    done = 0
    rng_seed = seed
    while done < n:
        m = min(chunk, n - done)
        _, hi, lo = price_paths(entry, bootstrap(moves, m, bars_left, block, rng_seed))
        rng_seed += 1
        if side == "buy":
            t_hit, s_hit = hi >= target, lo <= stop
        else:
            t_hit, s_hit = lo <= target, hi >= stop
        big = bars_left + 1
        t_first = np.where(t_hit.any(1), t_hit.argmax(1), big)
        s_first = np.where(s_hit.any(1), s_hit.argmax(1), big)
        hit_s[done:done + m] = (s_first <= t_first) & (s_first < big)
        hit_t[done:done + m] = (t_first < s_first)
        done += m
        if emit:
            publish("timemachine_progress", {"plan_id": plan_id, "done": done, "of": n})
    p_t, p_s = float(hit_t.mean()), float(hit_s.mean())
    p_o = 1 - p_t - p_s
    reward, risk = abs(target - entry), abs(entry - stop)
    costs = cost_points(market, entry) if market else 0.0
    ev = p_t * (reward - costs) - p_s * (risk + costs)
    res = {"replays": n, "bars_left": bars_left, "p_target": round(p_t * 100, 1), "p_stop": round(p_s * 100, 1),
           "p_open": round(p_o * 100, 1), "reward_pts": reward, "risk_pts": risk, "cost_pts": round(costs, 6),
           "ev_pts": round(ev, 6), "passed": ev > 0, "engine": "block-bootstrap", "block": block}
    if emit:
        publish("timemachine_done", {"plan_id": plan_id, **res})
    return res


def bars_left_in_session(market: str, last_bar: pd.Timestamp, tf_min: int, intraday: bool = True) -> int:
    """US equities: until 20:00 UTC (16:00 New York, ignoring DST shifts). FX/metals: until 21:00 UTC.
    Crypto / non-intraday: a fixed 32-bar horizon."""
    if not intraday or spec(market).session == "24x7":
        return 32
    end_h = 20 if spec(market).session == "us_equity" else 21
    t = pd.Timestamp(last_bar)
    t = t.tz_convert("UTC") if t.tzinfo else t.tz_localize("UTC")
    end = t.normalize() + pd.Timedelta(hours=end_h)
    if end <= t:
        end += pd.Timedelta(days=1)
    return max(1, int((end - t).total_seconds() // (tf_min * 60)))
