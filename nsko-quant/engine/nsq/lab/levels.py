"""Level map for NSKO-OF-1: prior-session volume profile (POC, VAH, VAL, LVNs), prior session
high/low, and fair value gaps on the higher timeframe. Every level is attached to the bars that
come AFTER it is known, so there is no look-ahead."""
from __future__ import annotations

import numpy as np
import pandas as pd

from nsq.data import profile
from nsq.data.markets import tf_minutes

from . import detectors
from .indicators import session_key


def prior_session_levels(df: pd.DataFrame, offset_hours: float = 0.0, bins: int = 40) -> pd.DataFrame:
    """Per bar: the PREVIOUS completed session's poc, vah, val, high, low, lvn (list).
    A session's levels are only attached to bars of the next session."""
    key = session_key(df.index, offset_hours)
    rows = {}
    kind = df.attrs.get("volume_kind", "exchange")
    for k, g in df.groupby(key, sort=True):
        pr = profile.from_candles(g, bins=bins, kind=kind)
        rows[k] = {"poc": pr["poc"], "vah": pr["vah"], "val": pr["val"], "lvn": tuple(pr["lvn"]),
                   "hvn": tuple(pr["hvn"]), "psh": float(g["high"].max()), "psl": float(g["low"].min())}
    keys = sorted(rows)
    prev = {keys[i]: rows[keys[i - 1]] for i in range(1, len(keys))}
    out = pd.DataFrame([prev.get(k, {}) for k in key], index=df.index,
                       columns=["poc", "vah", "val", "lvn", "hvn", "psh", "psl"])
    return out


def htf_fvgs(df: pd.DataFrame, htf: str, ltf_minutes: int) -> pd.DataFrame:
    """FVGs found on the higher timeframe, with `avail` = the open time of the first LTF bar at
    whose close the HTF bar that confirms the gap is complete."""
    from nsq.data.candles import resample
    if tf_minutes(htf) <= ltf_minutes:
        ev = detectors.fair_value_gaps(df)
        ev["avail"] = ev["time"]
        return ev
    h = resample(df, htf, drop_incomplete=False)
    ev = detectors.fair_value_gaps(h)
    ev["avail"] = ev["time"] + pd.Timedelta(minutes=tf_minutes(htf) - ltf_minutes)
    return ev


def market_state(close: np.ndarray, vah: np.ndarray, val: np.ndarray, accept_bars: int = 3) -> np.ndarray:
    """+1 imbalanced up (accepted above prior value), -1 imbalanced down, 0 balanced.
    'Accepted' = the last `accept_bars` closes all outside the prior value area."""
    above = pd.Series(close > vah).rolling(accept_bars, min_periods=accept_bars).sum().to_numpy() == accept_bars
    below = pd.Series(close < val).rolling(accept_bars, min_periods=accept_bars).sum().to_numpy() == accept_bars
    st = np.zeros(len(close), dtype=int)
    st[above] = 1
    st[below] = -1
    return st
