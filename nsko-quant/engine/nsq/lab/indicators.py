"""Causal indicators: every value at bar t uses bars <= t only (ewm / rolling / cumulative)."""
from __future__ import annotations

import numpy as np
import pandas as pd


def atr(df: pd.DataFrame, n: int = 14) -> pd.Series:
    pc = df["close"].shift(1)
    tr = pd.concat([df["high"] - df["low"], (df["high"] - pc).abs(), (df["low"] - pc).abs()], axis=1).max(axis=1)
    return tr.ewm(alpha=1.0 / n, adjust=False, min_periods=n).mean()


def ema(s: pd.Series, n: int) -> pd.Series:
    return s.ewm(span=n, adjust=False, min_periods=n).mean()


def session_key(index: pd.DatetimeIndex, offset_hours: float = 0.0) -> np.ndarray:
    """Trading-day id per bar. offset_hours=2 makes an FX/gold day start at 22:00 UTC."""
    shifted = index + pd.Timedelta(hours=offset_hours)
    return (shifted.normalize().as_unit("ns").asi8 // 86_400_000_000_000).astype(np.int64)


def session_offset(market: str) -> float:
    from nsq.data.markets import info
    return 2.0 if info(market).get("sessions") == "fx" else 0.0


def session_vwap(df: pd.DataFrame, offset_hours: float = 0.0) -> pd.Series:
    key = session_key(df.index, offset_hours)
    tp = (df["high"] + df["low"] + df["close"]) / 3
    v = df["volume"].clip(lower=0) + 1e-12
    pv = (tp * v).groupby(key).cumsum()
    vv = v.groupby(key).cumsum()
    return pv / vv


def rolling_median(s: pd.Series, n: int) -> pd.Series:
    return s.rolling(n, min_periods=max(3, n // 3)).median()


def in_sessions(index: pd.DatetimeIndex, sessions: list[str] | None) -> np.ndarray:
    """UTC session windows (bar open time). london 07:00-16:00, ny 12:30-20:00, asia 00:00-07:00."""
    if not sessions:
        return np.ones(len(index), dtype=bool)
    h = index.hour.values + index.minute.values / 60.0
    win = {"asia": (0.0, 7.0), "london": (7.0, 16.0), "ny": (12.5, 20.0), "us": (13.5, 20.0)}
    m = np.zeros(len(index), dtype=bool)
    for s in sessions:
        if s in ("24/7", "all"):
            return np.ones(len(index), dtype=bool)
        lo, hi = win.get(s, (0.0, 24.0))
        m |= (h >= lo) & (h < hi)
    return m
