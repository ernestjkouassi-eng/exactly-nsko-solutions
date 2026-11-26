"""Backtester with costs (8.4).

Fills: a signal on bar t fills at bar t+1's OPEN (we only know the signal at t's close).
Exits: the first later bar whose range touches the stop or the target. If one bar touches both,
the stop is assumed first (conservative). A bar that opens beyond the stop exits at that open
(gap). Unfinished trades close at the last bar's close, or after `max_hold` bars.
One position at a time; signals that arrive while a trade is open are skipped.

Costs, all per trade:
  spread       price units; you buy at mid + spread/2 and sell at mid - spread/2
  slippage     basis points of price on market fills (entry and stop exits; limit targets have none)
  commission   basis points of notional, each side
  funding      annual % of notional, charged per overnight rollover (22:00 UTC) held

Each trade's net P&L is expressed in R (planned risk = |entry fill - stop|). Equity compounds at
`risk_pct` of equity per trade. Exit search is vectorised per trade with numpy (argmax over the
future window), so a full history runs in seconds.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from nsq.data.markets import info

COST_DEFAULTS = {
    "crypto": {"spread": 0.0, "spread_bps": 2.0, "slippage_bps": 2.0, "commission_bps": 10.0, "funding_annual_pct": 0.0},
    "cfd": {"spread": 0.0, "spread_bps": 1.2, "slippage_bps": 0.5, "commission_bps": 0.0, "funding_annual_pct": 5.0},
    "equity": {"spread": 0.0, "spread_bps": 2.0, "slippage_bps": 1.0, "commission_bps": 1.0, "funding_annual_pct": 6.0},
    "other": {"spread": 0.0, "spread_bps": 2.0, "slippage_bps": 1.0, "commission_bps": 1.0, "funding_annual_pct": 5.0},
}


def costs_for(market: str) -> dict:
    kind = info(market).get("kind", "other")
    base = dict(COST_DEFAULTS.get(kind, COST_DEFAULTS["other"]))
    try:
        from nsq.data.util import setting
        base.update(setting(f"lab.costs.{kind}", {f"lab.costs.{kind}": {}}) or {})
    except Exception:
        pass
    return base


@dataclass
class Result:
    trades: pd.DataFrame
    equity: pd.Series                # equity after each trade, indexed by exit time (starts at 1.0)
    metrics: dict = field(default_factory=dict)


def _rollovers(t0: np.int64, t1: np.int64) -> int:
    """Number of 22:00 UTC rollovers strictly after t0 and at or before t1 (ns timestamps)."""
    day = 86_400_000_000_000
    off = 22 * 3_600_000_000_000
    return int(max(0, (t1 - off) // day - (t0 - off) // day))


def run(candles: pd.DataFrame, signals: list[dict], costs: dict | None = None, risk_pct: float = 1.0,
        max_hold: int = 500, ann_factor: float | None = None, market: str | None = None) -> Result:
    market = market or candles.attrs.get("market", "")
    costs = {**(costs_for(market) if costs is None else costs)}
    O, H, L, C = (candles[x].to_numpy(dtype=float) for x in ("open", "high", "low", "close"))
    ns = candles.index.as_unit("ns").asi8
    pos_of = {t: i for i, t in enumerate(ns)}
    n = len(candles)
    rows = []
    free_at = -1
    for s in sorted(signals, key=lambda x: x["time"]):
        t = pd.Timestamp(s["time"])
        t = (t.tz_localize("UTC") if t.tzinfo is None else t.tz_convert("UTC")).value
        i = pos_of.get(t)
        if i is None or i + 1 >= n or i < free_at:
            continue
        d = 1 if s["side"] == "buy" else -1
        stop, target = float(s["stop"]), float(s["target"])
        j = i + 1
        mid_in = O[j]
        half_spread = costs.get("spread", 0.0) / 2 + mid_in * costs.get("spread_bps", 0.0) / 2e4
        slip_in = mid_in * costs.get("slippage_bps", 0.0) / 1e4
        fill = mid_in + d * (half_spread + slip_in)
        risk = (fill - stop) * d
        if risk <= 0:            # the market already opened through the stop: no trade
            continue
        end = min(n, j + max_hold)
        hh, ll, oo = H[j:end], L[j:end], O[j:end]
        hit_stop = (ll <= stop) if d > 0 else (hh >= stop)
        hit_tgt = (hh >= target) if d > 0 else (ll <= target)
        ks = int(np.argmax(hit_stop)) if hit_stop.any() else None
        kt = int(np.argmax(hit_tgt)) if hit_tgt.any() else None
        if ks is not None and (kt is None or ks <= kt):
            k = ks
            gap = (oo[k] <= stop) if d > 0 else (oo[k] >= stop)
            mid_out = oo[k] if (gap and k > 0) else stop
            slip_out = mid_out * costs.get("slippage_bps", 0.0) / 1e4
            why = "stop"
        elif kt is not None:
            k = kt
            gap = (oo[k] >= target) if d > 0 else (oo[k] <= target)
            mid_out = oo[k] if (gap and k > 0) else target
            slip_out = 0.0
            why = "target"
        else:
            k = end - j - 1
            mid_out = C[j + k]
            slip_out = mid_out * costs.get("slippage_bps", 0.0) / 1e4
            why = "time" if end < n else "end"
        x = j + k
        half_spread_out = costs.get("spread", 0.0) / 2 + mid_out * costs.get("spread_bps", 0.0) / 2e4
        exit_px = mid_out - d * (half_spread_out + slip_out)
        gross = (exit_px - fill) * d
        comm = (fill + exit_px) * costs.get("commission_bps", 0.0) / 1e4
        nights = _rollovers(ns[j], ns[x])
        funding = fill * costs.get("funding_annual_pct", 0.0) / 100 / 365 * nights
        net = gross - comm - funding
        rows.append({"signal_time": pd.Timestamp(t, tz="UTC"), "entry_time": candles.index[j], "exit_time": candles.index[x],
                     "side": s["side"], "entry": fill, "exit": exit_px, "stop": stop, "target": target,
                     "risk": risk, "gross": gross, "commission": comm, "funding": funding, "nights": nights,
                     "r": net / risk, "r_gross": ((mid_out - mid_in) * d) / risk, "exit_reason": why, "bars": k + 1,
                     "reason": s.get("reason", "")})
        free_at = x   # a signal on the exit bar may fill on the next bar
    trades = pd.DataFrame(rows)
    eq = equity_from_r(trades, risk_pct, start=candles.index[0] if n else None)
    af = ann_factor or (365.0 if info(market).get("sessions") == "24/7" else 252.0)
    return Result(trades, eq, metrics(trades, eq, af))


def equity_from_r(trades: pd.DataFrame, risk_pct: float = 1.0, start=None) -> pd.Series:
    if not len(trades):
        return pd.Series([1.0], index=pd.DatetimeIndex([start] if start is not None else [pd.Timestamp(0, tz="UTC")]))
    eq = np.cumprod(1 + risk_pct / 100.0 * trades["r"].to_numpy())
    idx = pd.DatetimeIndex([start if start is not None else trades["entry_time"].iloc[0]]).append(pd.DatetimeIndex(trades["exit_time"]))
    return pd.Series(np.concatenate([[1.0], eq]), index=idx)


def max_drawdown_pct(eq: pd.Series | np.ndarray) -> float:
    v = np.asarray(eq, dtype=float)
    if not len(v):
        return 0.0
    peak = np.maximum.accumulate(v)
    return float((v / peak - 1).min() * 100)


def daily_returns(eq: pd.Series) -> pd.Series:
    if len(eq) < 2:
        return pd.Series(dtype=float)
    d = eq.groupby(eq.index.normalize()).last()
    full = d.reindex(pd.date_range(d.index[0], d.index[-1], freq="D", tz="UTC")).ffill()
    return full.pct_change().dropna()


def sharpe(daily: pd.Series, ann_factor: float = 252.0) -> float:
    if len(daily) < 2 or daily.std(ddof=1) == 0 or not np.isfinite(daily.std(ddof=1)):
        return 0.0
    return float(daily.mean() / daily.std(ddof=1) * np.sqrt(ann_factor))


def metrics(trades: pd.DataFrame, eq: pd.Series, ann_factor: float = 252.0) -> dict:
    if not len(trades):
        return {"trades": 0, "win": 0.0, "rr": 0.0, "expectancy_r": 0.0, "sharpe": 0.0, "dd": 0.0,
                "total_return_pct": 0.0, "profit_factor": 0.0, "avg_bars": 0.0}
    r = trades["r"].to_numpy()
    wins, losses = r[r > 0], r[r <= 0]
    rr = float(wins.mean() / abs(losses.mean())) if len(wins) and len(losses) and losses.mean() != 0 else float(len(wins) > 0) * 99.0
    pf = float(wins.sum() / abs(losses.sum())) if len(losses) and losses.sum() != 0 else 99.0
    return {"trades": int(len(r)), "win": round(float(len(wins) / len(r) * 100), 2), "rr": round(rr, 3),
            "expectancy_r": round(float(r.mean()), 4), "sharpe": round(sharpe(daily_returns(eq), ann_factor), 3),
            "dd": round(max_drawdown_pct(eq), 2), "total_return_pct": round(float((eq.iloc[-1] - 1) * 100), 2),
            "profit_factor": round(pf, 3), "avg_bars": round(float(trades["bars"].mean()), 1)}


def downsample(eq: pd.Series, points: int = 300) -> list[list[float]]:
    """[[ts_ms, equity], ...] with at most `points` points (keeps first and last)."""
    if not len(eq):
        return []
    idx = np.unique(np.linspace(0, len(eq) - 1, min(points, len(eq))).round().astype(int))
    return [[int(eq.index[i].value // 1_000_000), round(float(eq.iloc[i]), 6)] for i in idx]
