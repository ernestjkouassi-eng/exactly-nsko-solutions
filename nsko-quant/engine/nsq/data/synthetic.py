"""Seeded synthetic candles, used only when no real history is available.

Realism: GARCH(1,1) volatility clustering with fat-tailed (Student-t, 4 dof) shocks, scaled to the
market's typical annual volatility; an intraday activity curve (Asia quiet, London and New York
busy); slow drifting trend regimes; volume that rises with activity and with the size of the move;
weekend closures for gold/FX and US hours for shares. Every frame is flagged `synthetic=True`.

The same market + timeframe always produces the same series (seeded by a hash of the name), and a
series always starts from a fixed anchor date, so any window you ask for is a slice of one stable
history. Asking for a longer window never changes bars you already had.
"""
from __future__ import annotations

import zlib
from functools import lru_cache

import numpy as np
import pandas as pd

from .markets import info, norm, tf_minutes, to_utc


def _anchor(tf: str) -> pd.Timestamp:
    m = tf_minutes(tf)
    year = 2009 if m >= 15 else (2018 if m >= 5 else 2023)
    return pd.Timestamp(f"{year}-01-01", tz="UTC")


def _session_mask(idx: pd.DatetimeIndex, sessions: str) -> np.ndarray:
    dow = idx.dayofweek.values
    hour = idx.hour.values + idx.minute.values / 60.0
    if sessions == "fx":   # Sunday 22:00 UTC to Friday 21:00 UTC, with a 1 h daily break at 21:00
        open_ = ~((dow == 5) | ((dow == 6) & (hour < 22)) | ((dow == 4) & (hour >= 21)))
        return open_ & ~((hour >= 21) & (hour < 22))
    if sessions == "us":   # 14:30-21:00 UTC weekdays (DST ignored for synthetic data)
        return (dow < 5) & (hour >= 14.5) & (hour < 21)
    return np.ones(len(idx), dtype=bool)


def _activity(idx: pd.DatetimeIndex) -> np.ndarray:
    h = idx.hour.values + idx.minute.values / 60.0
    london = np.exp(-0.5 * ((h - 9.0) / 2.0) ** 2)
    ny = 1.3 * np.exp(-0.5 * ((h - 14.5) / 2.2) ** 2)
    return 0.45 + london + ny   # Asia ~0.45, NY open peak ~1.75


@lru_cache(maxsize=16)
def _series(market: str, tf: str, last_year: int) -> pd.DataFrame:
    """Whole calendar years from the anchor to `last_year`. Each year has its own seeded random
    stream and carries the state (volatility, drift, price) over from the year before, so adding a
    year never changes earlier bars."""
    meta = info(market)
    mins = tf_minutes(tf)
    bars_per_year = 365 * 1440 / mins if meta["sessions"] == "24/7" else 252 * (1440 if meta["sessions"] == "fx" else 390) / mins
    base_sig = meta["ann_vol"] / np.sqrt(bars_per_year)
    a, b = 0.06, 0.92
    w = 1 - a - b
    k = 1.0 / max(50, int(5 * 1440 / mins))
    vol_base = 1000.0 if meta["volume_kind"] == "tick" else 50.0
    dp = 2 if meta["px"] > 50 else 4
    hv, d = 1.0, 0.0
    lref = float(np.log(meta["px"]))
    kappa = 1.0 / bars_per_year
    px = meta["px"] * 0.7
    frames = []
    for year in range(_anchor(tf).year, last_year + 1):
        idx = pd.date_range(f"{year}-01-01", f"{year + 1}-01-01", freq=f"{mins}min", inclusive="left", tz="UTC")
        idx = idx[_session_mask(idx, meta["sessions"])]
        n = len(idx)
        rng = np.random.default_rng([zlib.crc32(f"{norm(market)}|{tf}".encode()), year])
        act = _activity(idx) if meta["sessions"] != "us" else np.ones(n)
        act = act / 1.0
        z = rng.standard_t(4, size=n) / np.sqrt(2.0)          # t(4) scaled to unit variance
        dz = rng.standard_normal(n)
        wick = np.abs(rng.standard_normal((2, n)))
        vn = rng.standard_normal(n)
        sig = base_sig * np.sqrt(act)
        r = np.empty(n)
        lp = np.log(px)
        for i in range(n):
            ei = z[i] * np.sqrt(hv)
            hv = w + a * ei * ei + b * hv
            d = d * (1 - k) + np.sqrt(2 * k) * dz[i]
            # shock + slow trend regime + a weak pull back towards the reference price over ~1 year
            ri = sig[i] * (ei + 0.04 * d) - kappa * (lp - lref)
            lp += ri
            r[i] = ri
        close = np.exp(np.cumsum(r) + np.log(px))
        open_ = np.empty(n)
        open_[0] = px
        open_[1:] = close[:-1]
        px = float(close[-1])
        high = np.maximum(open_, close) * np.exp(wick[0] * sig * 0.6)
        low = np.minimum(open_, close) / np.exp(wick[1] * sig * 0.6)
        volume = vol_base * act * (0.6 + np.abs(r) / base_sig * 0.5) * np.exp(vn * 0.25)
        if meta["volume_kind"] == "tick":
            volume = np.round(volume)
        frames.append(pd.DataFrame({"open": open_.round(dp), "high": high.round(dp), "low": low.round(dp),
                                    "close": close.round(dp), "volume": volume.round(4)}, index=idx))
    df = pd.concat(frames)
    df.index.name = "time"
    return df


def candles(market: str, timeframe: str, start, end) -> pd.DataFrame:
    s, e = to_utc(start), to_utc(end)
    anchor = _anchor(timeframe)
    if s < anchor:
        s = anchor
    full = _series(norm(market), timeframe, int((e - pd.Timedelta(microseconds=1)).year))
    df = full.loc[(full.index >= s) & (full.index < e)].copy()
    df.attrs.update({"synthetic": True, "source": "synthetic (seeded)", "market": norm(market),
                     "timeframe": timeframe, "volume_kind": "synthetic-" + info(market)["volume_kind"]})
    return df
