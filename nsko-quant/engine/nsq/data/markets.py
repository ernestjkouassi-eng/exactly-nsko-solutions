"""Market catalogue: names used by the UI, Kraken pairs, volume kind and synthetic parameters."""
from __future__ import annotations

import pandas as pd

TF_MINUTES = {"1m": 1, "3m": 3, "5m": 5, "15m": 15, "30m": 30, "1h": 60, "4h": 240, "1d": 1440, "1w": 10080}
KRAKEN_INTERVALS = (1, 5, 15, 30, 60, 240, 1440, 10080, 21600)   # minutes, per Kraken OHLC docs

MARKETS: dict[str, dict] = {
    # crypto: Kraken public data has real exchange volume
    "BTC/USD": {"kind": "crypto", "kraken_rest": "XBTUSD", "kraken_ws": "BTC/USD", "px": 60000.0, "ann_vol": 0.60,
                "volume_kind": "exchange", "sessions": "24/7", "tick": 0.1},
    "ETH/USD": {"kind": "crypto", "kraken_rest": "ETHUSD", "kraken_ws": "ETH/USD", "px": 3000.0, "ann_vol": 0.75,
                "volume_kind": "exchange", "sessions": "24/7", "tick": 0.01},
    "SOL/USD": {"kind": "crypto", "kraken_rest": "SOLUSD", "kraken_ws": "SOL/USD", "px": 150.0, "ann_vol": 0.95,
                "volume_kind": "exchange", "sessions": "24/7", "tick": 0.01},
    # gold is a CFD at the broker: no exchange volume, only tick counts ("tick volume")
    "XAU/USD": {"kind": "cfd", "kraken_rest": None, "kraken_ws": None, "px": 2650.0, "ann_vol": 0.15,
                "volume_kind": "tick", "sessions": "fx", "tick": 0.01},
    "XAG/USD": {"kind": "cfd", "kraken_rest": None, "kraken_ws": None, "px": 31.0, "ann_vol": 0.28,
                "volume_kind": "tick", "sessions": "fx", "tick": 0.001},
    "NVDA": {"kind": "equity", "kraken_rest": None, "kraken_ws": None, "px": 140.0, "ann_vol": 0.50,
             "volume_kind": "exchange", "sessions": "us", "tick": 0.01},
    "AAPL": {"kind": "equity", "kraken_rest": None, "kraken_ws": None, "px": 230.0, "ann_vol": 0.28,
             "volume_kind": "exchange", "sessions": "us", "tick": 0.01},
}
ALIASES = {"XAU": "XAU/USD", "GOLD": "XAU/USD", "BTC": "BTC/USD", "XBT/USD": "BTC/USD", "ETH": "ETH/USD",
           "XAG": "XAG/USD", "SOL": "SOL/USD"}


def norm(market: str) -> str:
    m = market.strip().upper()
    return ALIASES.get(m, m)


def info(market: str) -> dict:
    m = norm(market)
    return MARKETS.get(m, {"kind": "other", "kraken_rest": None, "kraken_ws": None, "px": 100.0, "ann_vol": 0.3,
                           "volume_kind": "unknown", "sessions": "24/7", "tick": 0.01})


def tf_minutes(tf: str) -> int:
    if tf not in TF_MINUTES:
        raise ValueError(f"unknown timeframe {tf!r}; use one of {list(TF_MINUTES)}")
    return TF_MINUTES[tf]


def pandas_rule(tf: str) -> str:
    m = tf_minutes(tf)
    return f"{m}min"


def to_utc(t) -> pd.Timestamp:
    ts = pd.Timestamp(t)
    return ts.tz_localize("UTC") if ts.tzinfo is None else ts.tz_convert("UTC")
