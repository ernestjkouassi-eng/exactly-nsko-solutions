"""Volume profile maths: POC, value area high/low (70 %), low- and high-volume nodes.

`from_trades` uses real trade-by-trade volume (crypto via the Kraken trade stream).
`from_candles` spreads each bar's volume evenly over its high-low range. For gold (a CFD) the bar
"volume" is a tick count, so the result is a TICK-VOLUME profile and is labelled that way.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def _edges(lo: float, hi: float, bins: int) -> np.ndarray:
    if not np.isfinite(lo) or not np.isfinite(hi) or hi <= lo:
        hi = lo + max(abs(lo) * 1e-4, 1e-9)
    return np.linspace(lo, hi, bins + 1)


def summarise(edges: np.ndarray, vol: np.ndarray, value_area: float = 0.70, kind: str = "exchange") -> dict:
    """POC / VAH / VAL / LVN / HVN from a histogram."""
    mids = (edges[:-1] + edges[1:]) / 2
    total = float(vol.sum())
    if total <= 0:
        return {"poc": None, "vah": None, "val": None, "lvn": [], "hvn": [], "bins": [], "volume_kind": kind, "total": 0.0}
    p = int(np.argmax(vol))
    lo = hi = p
    acc = vol[p]
    while acc < value_area * total and (lo > 0 or hi < len(vol) - 1):
        up = vol[hi + 1] if hi < len(vol) - 1 else -1
        dn = vol[lo - 1] if lo > 0 else -1
        if up >= dn:
            hi += 1; acc += vol[hi]
        else:
            lo -= 1; acc += vol[lo]
    sm = np.convolve(vol, np.ones(3) / 3, mode="same")
    peak = sm.max()
    lvn, hvn = [], []
    for i in range(1, len(sm) - 1):
        if sm[i] < sm[i - 1] and sm[i] <= sm[i + 1] and sm[i] < 0.25 * peak:
            lvn.append(float(mids[i]))
        if sm[i] > sm[i - 1] and sm[i] >= sm[i + 1] and sm[i] > 0.6 * peak:
            hvn.append(float(mids[i]))
    return {"poc": float(mids[p]), "vah": float(edges[hi + 1]), "val": float(edges[lo]),
            "lvn": lvn, "hvn": hvn, "volume_kind": kind, "total": total,
            "bins": [{"price": float(m), "vol": float(v)} for m, v in zip(mids, vol)]}


def from_trades(prices, qtys, bins: int = 48, value_area: float = 0.70, kind: str = "exchange") -> dict:
    prices = np.asarray(prices, float)
    qtys = np.asarray(qtys, float)
    if not len(prices):
        return summarise(np.array([0.0, 1.0]), np.zeros(1), value_area, kind)
    edges = _edges(prices.min(), prices.max(), bins)
    vol, _ = np.histogram(prices, bins=edges, weights=qtys)
    return summarise(edges, vol, value_area, kind)


def from_candles(df: pd.DataFrame, bins: int = 48, value_area: float = 0.70, kind: str | None = None) -> dict:
    """Spread each bar's volume uniformly over [low, high]. Vectorised over bins."""
    kind = kind or df.attrs.get("volume_kind", "exchange")
    if not len(df):
        return summarise(np.array([0.0, 1.0]), np.zeros(1), value_area, kind)
    lo, hi = float(df["low"].min()), float(df["high"].max())
    edges = _edges(lo, hi, bins)
    l = df["low"].to_numpy(float)[:, None]
    h = df["high"].to_numpy(float)[:, None]
    v = df["volume"].to_numpy(float)[:, None]
    e0, e1 = edges[None, :-1], edges[None, 1:]
    overlap = np.clip(np.minimum(h, e1) - np.maximum(l, e0), 0, None)
    rng = np.maximum(h - l, 1e-12)
    point = (h - l) <= 1e-12
    share = np.where(point, ((l >= e0) & (l < e1)).astype(float), overlap / rng)
    vol = (share * v).sum(axis=0)
    out = summarise(edges, vol, value_area, kind)
    if "tick" in str(kind):
        out["label"] = "tick-volume profile (CFD: no exchange volume)"
    else:
        out["label"] = "volume profile"
    return out
