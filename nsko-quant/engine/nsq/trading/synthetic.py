"""Seeded synthetic candles, used only when nsq.data.candles is missing. Flagged synthetic=True."""
from __future__ import annotations

import numpy as np
import pandas as pd

_TF_MIN = {"1m": 1, "5m": 5, "15m": 15, "30m": 30, "1h": 60, "4h": 240, "1d": 1440}
_BASE = {"XAU/USD": (2648.4, 0.0012), "BTC/USD": (97240, 0.004), "ETH/USD": (3612, 0.005),
         "NVDA": (141.2, 0.003), "AAPL": (232.6, 0.002), "EUR/USD": (1.05, 0.0006)}


def tf_minutes(tf: str) -> int:
    return _TF_MIN.get(tf, 15)


def synthetic_candles(market: str, timeframe: str = "15m", n: int = 500, seed: int = 7,
                      end: pd.Timestamp | None = None, drift: float = 0.0) -> pd.DataFrame:
    px0, vol = _BASE.get(market, (100.0, 0.002))
    rng = np.random.default_rng(seed + sum(map(ord, market)))
    rets = rng.normal(drift, vol, n)
    close = px0 * np.exp(np.cumsum(rets))
    open_ = np.concatenate([[px0], close[:-1]])
    wig = np.abs(rng.normal(0, vol / 2, n)) * close
    high = np.maximum(open_, close) + wig
    low = np.minimum(open_, close) - wig
    volume = rng.lognormal(5, 0.6, n)
    end = end if end is not None else pd.Timestamp.now(tz="UTC").floor(f"{tf_minutes(timeframe)}min")
    idx = pd.date_range(end=end, periods=n, freq=f"{tf_minutes(timeframe)}min", tz="UTC")
    df = pd.DataFrame({"open": open_, "high": high, "low": low, "close": close, "volume": volume}, index=idx)
    df.attrs["synthetic"] = True
    df.attrs["market"] = market
    return df
