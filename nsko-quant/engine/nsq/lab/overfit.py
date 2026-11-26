"""Overfitting checks (8.4).

- `sharpe_decline(is, oos)`: how much of the in-sample Sharpe survives out of sample.
- `pbo_cscv(M, S)`: probability of backtest overfitting by combinatorially symmetric cross-
  validation (Bailey, Borwein, Lopez de Prado & Zhu, 2014). M is T x N (periods x variants) of
  returns. Split the T rows into S blocks; for every way to pick S/2 blocks as IS, take the variant
  with the best IS Sharpe and find its relative rank OOS. PBO = share of splits where that best-IS
  variant lands in the bottom half OOS (logit <= 0).
- `chance_score(...)`: how the strategy ranks against random entries with the same number of
  trades, sides and stop/target distances.
- `monte_carlo_dd(r)`: reshuffle (and bootstrap) the trade sequence to get drawdown odds.
"""
from __future__ import annotations

from itertools import combinations

import numpy as np
import pandas as pd


def sharpe_decline(sharpe_is: float, sharpe_oos: float) -> float:
    """Fraction of IS Sharpe lost OOS: 0 = none lost, 1 = all lost, >1 = OOS negative."""
    if sharpe_is <= 0:
        return 0.0 if sharpe_oos >= sharpe_is else 1.0
    return float(max(0.0, (sharpe_is - sharpe_oos) / sharpe_is))


def _sr(x: np.ndarray) -> np.ndarray:
    sd = x.std(axis=0, ddof=1)
    mu = x.mean(axis=0)
    with np.errstate(divide="ignore", invalid="ignore"):
        out = np.where(sd > 0, mu / sd, 0.0)
    return out


def pbo_cscv(M: np.ndarray | pd.DataFrame, S: int = 16, max_splits: int = 5000, seed: int = 0) -> dict:
    M = np.asarray(M, dtype=float)
    T, N = M.shape
    if N < 2 or T < S * 2:
        return {"pbo": None, "splits": 0, "logits": [], "note": "need >= 2 variants and >= 2*S periods"}
    S = S - (S % 2)
    blocks = np.array_split(np.arange(T), S)
    combos = list(combinations(range(S), S // 2))
    if len(combos) > max_splits:
        rng = np.random.default_rng(seed)
        combos = [combos[i] for i in rng.choice(len(combos), max_splits, replace=False)]
    logits = []
    for c in combos:
        is_rows = np.concatenate([blocks[k] for k in c])
        oos_rows = np.concatenate([blocks[k] for k in range(S) if k not in c])
        sr_is, sr_oos = _sr(M[is_rows]), _sr(M[oos_rows])
        best = int(np.argmax(sr_is))
        rank = (sr_oos < sr_oos[best]).sum() + 0.5 * ((sr_oos == sr_oos[best]).sum() - 1) + 1  # 1..N
        w = rank / (N + 1)
        logits.append(float(np.log(w / (1 - w))))
    lg = np.array(logits)
    return {"pbo": float((lg <= 0).mean()), "splits": len(lg), "logits": [round(x, 4) for x in lg[:200]]}


def returns_matrix(equities: list[pd.Series], freq: str = "W") -> np.ndarray:
    """Align several equity curves into a T x N matrix of period returns (default weekly)."""
    cols = []
    for eq in equities:
        d = eq.groupby(eq.index.normalize()).last()
        cols.append(d)
    df = pd.concat(cols, axis=1)
    full = df.reindex(pd.date_range(df.index.min(), df.index.max(), freq="D", tz="UTC")).ffill().fillna(1.0)
    per = full.resample(freq).last()
    return per.pct_change().dropna().to_numpy()


def chance_score(candles: pd.DataFrame, signals: list[dict], actual_metric: float, n_random: int = 100,
                 metric: str = "expectancy_r", seed: int = 7, **bt_kw) -> dict:
    """Percentile of the actual metric among `n_random` random-entry strategies (same trade count,
    same sides, same stop/target distances as % of entry). 95 means it beat 95 % of random runs."""
    from .backtest import run
    if not signals:
        return {"percentile": 0.0, "n": 0, "random_median": None}
    rng = np.random.default_rng(seed)
    n = len(candles)
    C = candles["close"].to_numpy()
    dists = [((s["entry"] - s["stop"]) / s["entry"], (s["target"] - s["entry"]) / s["entry"], s["side"]) for s in signals]
    vals = []
    for _ in range(n_random):
        pos = np.sort(rng.choice(np.arange(20, n - 2), size=min(len(signals), max(1, n - 22)), replace=False))
        rs = []
        for p, (ds, dt, side) in zip(pos, dists):
            e = C[p]
            rs.append({"time": candles.index[p].isoformat(), "side": side, "entry": e, "stop": e * (1 - ds),
                       "target": e * (1 + dt), "reason": "random"})
        vals.append(run(candles, rs, **bt_kw).metrics.get(metric, 0.0))
    v = np.array(vals)
    return {"percentile": round(float((v < actual_metric).mean() * 100), 1), "n": int(n_random),
            "random_median": round(float(np.median(v)), 4), "metric": metric}


def monte_carlo_dd(r: np.ndarray, risk_pct: float = 1.0, n: int = 1000, seed: int = 11,
                   bad_dd_pct: float = -20.0, bootstrap: bool = True) -> dict:
    """Drawdown odds from reshuffled trade order (and bootstrap resampling).
    Returns percentiles of max drawdown (%) and the chance of a drawdown worse than bad_dd_pct, plus
    a small fan (p5/p50/p95 equity paths, 60 points) for the UI."""
    r = np.asarray(r, dtype=float)
    if len(r) < 2:
        return {"n": 0, "dd_p50": 0.0, "dd_p95": 0.0, "p_bad": 0.0, "fan": {}}
    rng = np.random.default_rng(seed)
    k = len(r)
    paths = np.empty((n, k))
    for i in range(n):
        seq = rng.choice(r, size=k, replace=True) if bootstrap else rng.permutation(r)
        paths[i] = np.cumprod(1 + risk_pct / 100 * seq)
    peak = np.maximum.accumulate(paths, axis=1)
    dd = ((paths / peak - 1).min(axis=1)) * 100
    pts = np.unique(np.linspace(0, k - 1, min(60, k)).round().astype(int))
    fan = {f"p{q}": [round(float(x), 5) for x in np.percentile(paths[:, pts], q, axis=0)] for q in (5, 50, 95)}
    return {"n": n, "dd_p50": round(float(np.percentile(dd, 50)), 2), "dd_p95": round(float(np.percentile(dd, 5)), 2),
            "p_bad": round(float((dd < bad_dd_pct).mean() * 100), 1), "bad_dd_pct": bad_dd_pct, "fan": fan}
