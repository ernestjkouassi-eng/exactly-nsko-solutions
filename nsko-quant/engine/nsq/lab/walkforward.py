"""Walk-forward split (8.4): in-sample 2009-2019, out-of-sample 2020-now, or whatever history exists.

If the data does not reach both sides of the default boundary with enough on each side, the split
falls back to the first `fallback_is_frac` of the time span as IS and the rest as OOS.
The OOS window is never used to choose parameters; it is only scored.
"""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

DEFAULT_IS_START = "2009-01-01"
DEFAULT_OOS_START = "2020-01-01"


@dataclass
class Split:
    is_start: pd.Timestamp
    oos_start: pd.Timestamp
    end: pd.Timestamp
    mode: str           # "calendar" (2009-2019 / 2020-now) or "fraction"

    def as_dict(self) -> dict:
        return {"is": [self.is_start.isoformat(), self.oos_start.isoformat()],
                "oos": [self.oos_start.isoformat(), self.end.isoformat()], "mode": self.mode}

    def is_mask(self, times) -> pd.Series:
        t = pd.DatetimeIndex(times)
        return (t >= self.is_start) & (t < self.oos_start)

    def oos_mask(self, times) -> pd.Series:
        t = pd.DatetimeIndex(times)
        return (t >= self.oos_start) & (t <= self.end)


def split(index: pd.DatetimeIndex, oos_start: str = DEFAULT_OOS_START, is_start: str = DEFAULT_IS_START,
          min_side_frac: float = 0.15, fallback_is_frac: float = 0.7) -> Split:
    if not len(index):
        raise ValueError("no data to split")
    first, last = index[0], index[-1]
    span = last - first
    b = pd.Timestamp(oos_start, tz="UTC")
    s0 = max(first, pd.Timestamp(is_start, tz="UTC"))
    if first < b < last and (b - s0) >= min_side_frac * span and (last - b) >= min_side_frac * span:
        return Split(s0, b, last, "calendar")
    cut = first + fallback_is_frac * span
    return Split(first, cut, last, "fraction")


def split_trades(trades: pd.DataFrame, sp: Split) -> tuple[pd.DataFrame, pd.DataFrame]:
    if not len(trades):
        return trades, trades
    t = trades["entry_time"]
    return trades[sp.is_mask(t)], trades[sp.oos_mask(t)]
