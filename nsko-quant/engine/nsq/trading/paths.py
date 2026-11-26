"""Block-bootstrap path generator (shared by the forecast fallback and the Time Machine).

Samples contiguous blocks of the market's own recent bars (as relative moves: close-to-close log return,
plus the high and low excursions from each bar's open), and strings them together. Contiguous blocks keep
the short-range autocorrelation and volatility clustering that an i.i.d. bootstrap would destroy.
Only CLOSED bars passed in are used.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def bar_moves(df: pd.DataFrame) -> np.ndarray:
    """(n-1, 3) array of [log(close/prev_close), log(high/open'), log(low/open')] where open' = prev close."""
    c = df["close"].to_numpy(dtype=float)
    h = df["high"].to_numpy(dtype=float)
    lo = df["low"].to_numpy(dtype=float)
    prev = c[:-1]
    ret = np.log(c[1:] / prev)
    up = np.log(np.maximum(h[1:], np.maximum(prev, c[1:])) / prev)
    dn = np.log(np.minimum(lo[1:], np.minimum(prev, c[1:])) / prev)
    return np.stack([ret, up, dn], axis=1)


def bootstrap(moves: np.ndarray, n_paths: int, horizon: int, block: int = 8, seed: int | None = 0) -> np.ndarray:
    """Returns (n_paths, horizon, 3) sampled moves."""
    n = len(moves)
    if n < 2:
        raise ValueError("need at least 3 closed bars to bootstrap")
    block = max(1, min(block, n))
    rng = np.random.default_rng(seed)
    n_blocks = -(-horizon // block)
    starts = rng.integers(0, n - block + 1, size=(n_paths, n_blocks))
    idx = (starts[:, :, None] + np.arange(block)[None, None, :]).reshape(n_paths, -1)[:, :horizon]
    return moves[idx]


def price_paths(last_close: float, sampled: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """From sampled moves build close, high and low paths, each (n_paths, horizon)."""
    cum = np.cumsum(sampled[:, :, 0], axis=1)
    close = last_close * np.exp(cum)
    prev = np.concatenate([np.full((sampled.shape[0], 1), last_close), close[:, :-1]], axis=1)
    high = prev * np.exp(sampled[:, :, 1])
    low = prev * np.exp(sampled[:, :, 2])
    return close, high, low
