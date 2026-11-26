"""Knowledge Base detectors (8.5). Pure functions on closed candles.

Each detector returns a DataFrame of events with columns
  time    bar at which the pattern is CONFIRMED (known at that bar's close; never earlier)
  origin  bar where the pattern starts (may be earlier than `time`)
  dir     +1 bullish / -1 bearish
  top, bottom   price zone (or the level, top == bottom)
  size    zone height in price units
So a strategy may use an event at bar t only if event.time <= t. No detector looks ahead.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .indicators import atr

EV_COLS = ["time", "origin", "dir", "top", "bottom", "size"]


def _ev(rows: list[tuple]) -> pd.DataFrame:
    df = pd.DataFrame(rows, columns=EV_COLS)
    if len(df):
        df["time"] = pd.to_datetime(df["time"], utc=True)
        df["origin"] = pd.to_datetime(df["origin"], utc=True)
    return df


def swings(df: pd.DataFrame, n: int = 3) -> pd.DataFrame:
    """Fractal swing highs/lows: bar j is a swing high if its high is the highest of j-n..j+n.
    Confirmed at bar j+n (we must wait n bars to know)."""
    h, l = df["high"].to_numpy(), df["low"].to_numpy()
    idx = df.index
    w = 2 * n + 1
    rh = pd.Series(h).rolling(w).max().to_numpy()
    rl = pd.Series(l).rolling(w).min().to_numpy()
    rows = []
    for i in range(w - 1, len(df)):
        j = i - n
        if h[j] == rh[i] and np.sum(h[i - w + 1:i + 1] == h[j]) == 1:
            rows.append((idx[i], idx[j], -1, h[j], h[j], 0.0))   # swing high (resistance)
        if l[j] == rl[i] and np.sum(l[i - w + 1:i + 1] == l[j]) == 1:
            rows.append((idx[i], idx[j], +1, l[j], l[j], 0.0))   # swing low (support)
    return _ev(rows)


def fair_value_gaps(df: pd.DataFrame, min_atr: float = 0.0) -> pd.DataFrame:
    """Three-bar imbalance. Bullish: low[t] > high[t-2] (gap = [high[t-2], low[t]]). Bearish mirror.
    Known at the close of bar t."""
    h, l = df["high"].to_numpy(), df["low"].to_numpy()
    a = atr(df).to_numpy()
    idx = df.index
    rows = []
    for t in range(2, len(df)):
        thr = min_atr * a[t] if min_atr and np.isfinite(a[t]) else 0.0
        if l[t] > h[t - 2] and l[t] - h[t - 2] > thr:
            rows.append((idx[t], idx[t - 1], +1, l[t], h[t - 2], l[t] - h[t - 2]))
        elif h[t] < l[t - 2] and l[t - 2] - h[t] > thr:
            rows.append((idx[t], idx[t - 1], -1, l[t - 2], h[t], l[t - 2] - h[t]))
    return _ev(rows)


def displacement(df: pd.DataFrame, k: float = 1.5, body_frac: float = 0.6) -> pd.DataFrame:
    """A strong one-bar move: body > k x ATR(previous bar) and body >= body_frac of the range."""
    o, c, h, l = (df[x].to_numpy() for x in ("open", "close", "high", "low"))
    a = atr(df).shift(1).to_numpy()
    body = np.abs(c - o)
    rng = np.maximum(h - l, 1e-12)
    m = np.isfinite(a) & (body > k * a) & (body / rng >= body_frac)
    rows = [(df.index[i], df.index[i], int(np.sign(c[i] - o[i])), max(o[i], c[i]), min(o[i], c[i]), body[i])
            for i in np.flatnonzero(m)]
    return _ev(rows)


def structure(df: pd.DataFrame, n: int = 3) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Break of structure (BOS) and change of character (CHoCH).
    A close beyond the last confirmed swing high (low) is a break up (down). If it agrees with the
    current trend (the direction of the previous break) it is a BOS; if it flips the trend, CHoCH."""
    sw = swings(df, n)
    c = df["close"].to_numpy()
    idx = df.index
    pos = {t: i for i, t in enumerate(idx)}
    sh_at = {pos[r.time]: r.top for r in sw.itertuples() if r.dir == -1}
    sl_at = {pos[r.time]: r.bottom for r in sw.itertuples() if r.dir == +1}
    last_sh = last_sl = None
    sh_origin = sl_origin = None
    origin_of = {pos[r.time]: r.origin for r in sw.itertuples()}
    trend = 0
    bos, choch = [], []
    for i in range(len(df)):
        if i in sh_at:
            last_sh, sh_origin = sh_at[i], origin_of[i]
        if i in sl_at:
            last_sl, sl_origin = sl_at[i], origin_of[i]
        if last_sh is not None and c[i] > last_sh and (i == 0 or c[i - 1] <= last_sh):
            (bos if trend >= 0 else choch).append((idx[i], sh_origin, +1, last_sh, last_sh, c[i] - last_sh))
            trend = +1
            last_sh = None          # a level breaks once
        elif last_sl is not None and c[i] < last_sl and (i == 0 or c[i - 1] >= last_sl):
            (bos if trend <= 0 else choch).append((idx[i], sl_origin, -1, last_sl, last_sl, last_sl - c[i]))
            trend = -1
            last_sl = None
    return _ev(bos), _ev(choch)


def break_of_structure(df: pd.DataFrame, n: int = 3) -> pd.DataFrame:
    return structure(df, n)[0]


def change_of_character(df: pd.DataFrame, n: int = 3) -> pd.DataFrame:
    return structure(df, n)[1]


def liquidity_sweeps(df: pd.DataFrame, n: int = 3) -> pd.DataFrame:
    """Wick through the last confirmed swing low (high) and a close back above (below) it.
    Bullish sweep = sell-side liquidity taken, then reclaimed."""
    sw = swings(df, n)
    h, l, c = df["high"].to_numpy(), df["low"].to_numpy(), df["close"].to_numpy()
    idx = df.index
    pos = {t: i for i, t in enumerate(idx)}
    sh_at = {pos[r.time]: (r.top, r.origin) for r in sw.itertuples() if r.dir == -1}
    sl_at = {pos[r.time]: (r.bottom, r.origin) for r in sw.itertuples() if r.dir == +1}
    lsh = lsl = None
    rows = []
    for i in range(len(df)):
        if lsl is not None and l[i] < lsl[0] and c[i] > lsl[0]:
            rows.append((idx[i], lsl[1], +1, lsl[0], l[i], lsl[0] - l[i]))
            lsl = None
        if lsh is not None and h[i] > lsh[0] and c[i] < lsh[0]:
            rows.append((idx[i], lsh[1], -1, h[i], lsh[0], h[i] - lsh[0]))
            lsh = None
        # a swing confirmed at bar i becomes usable from bar i+1
        if i in sh_at:
            lsh = sh_at[i]
        if i in sl_at:
            lsl = sl_at[i]
    return _ev(rows)


def order_blocks(df: pd.DataFrame, n: int = 3, lookback: int = 10) -> pd.DataFrame:
    """Bullish order block: the last bearish candle before the move that made a bullish BOS/CHoCH.
    Zone = that candle's low..high, confirmed at the break bar. Bearish mirror."""
    bos, choch = structure(df, n)
    brk = pd.concat([bos, choch]).sort_values("time")
    o, c, h, l = (df[x].to_numpy() for x in ("open", "close", "high", "low"))
    pos = {t: i for i, t in enumerate(df.index)}
    rows = []
    for r in brk.itertuples():
        i = pos[r.time]
        for j in range(i - 1, max(-1, i - lookback - 1), -1):
            if (r.dir == +1 and c[j] < o[j]) or (r.dir == -1 and c[j] > o[j]):
                rows.append((r.time, df.index[j], r.dir, h[j], l[j], h[j] - l[j]))
                break
    return _ev(rows)


def equal_levels(df: pd.DataFrame, n: int = 3, tol_atr: float = 0.1) -> pd.DataFrame:
    """Equal highs / equal lows (resting liquidity): two consecutive confirmed swings within
    tol_atr x ATR of each other. dir -1 = equal highs (buy stops above), +1 = equal lows."""
    sw = swings(df, n)
    a = atr(df)
    rows = []
    for d in (-1, +1):
        s = sw[sw.dir == d].reset_index(drop=True)
        for k in range(1, len(s)):
            av = a.get(s.time[k], np.nan)
            lvl0, lvl1 = s.top[k - 1], s.top[k]
            if np.isfinite(av) and abs(lvl1 - lvl0) <= tol_atr * av:
                rows.append((s.time[k], s.origin[k - 1], d, max(lvl0, lvl1), min(lvl0, lvl1), abs(lvl1 - lvl0)))
    return _ev(rows).sort_values("time").reset_index(drop=True) if rows else _ev([])


def inside_bars(df: pd.DataFrame) -> pd.DataFrame:
    h, l = df["high"].to_numpy(), df["low"].to_numpy()
    m = np.zeros(len(df), dtype=bool)
    m[1:] = (h[1:] <= h[:-1]) & (l[1:] >= l[:-1])
    return _ev([(df.index[i], df.index[i - 1], 0, h[i - 1], l[i - 1], h[i - 1] - l[i - 1]) for i in np.flatnonzero(m)])


def session_range(df: pd.DataFrame, start_h: float = 0.0, end_h: float = 7.0) -> pd.DataFrame:
    """Range of a session window (default Asia 00:00-07:00 UTC), confirmed at its last bar."""
    h = df.index.hour + df.index.minute / 60.0
    m = (h >= start_h) & (h < end_h)
    sub = df[m]
    rows = []
    for _, g in sub.groupby(sub.index.normalize()):
        rows.append((g.index[-1], g.index[0], 0, g["high"].max(), g["low"].min(), g["high"].max() - g["low"].min()))
    return _ev(rows)


def opening_range(df: pd.DataFrame, open_h: float = 7.0, minutes: int = 30) -> pd.DataFrame:
    return session_range(df, open_h, open_h + minutes / 60.0)


DETECTORS = {
    "fair_value_gap": fair_value_gaps, "order_block": order_blocks, "liquidity_sweep": liquidity_sweeps,
    "break_of_structure": break_of_structure, "change_of_character": change_of_character,
    "displacement": displacement, "swing_point": swings, "equal_highs_lows": equal_levels,
    "inside_bar": inside_bars, "asia_range": session_range, "opening_range": opening_range,
}


def zone_stats(df: pd.DataFrame, ev: pd.DataFrame, max_bars: int = 200) -> dict:
    """Descriptive stats on the client's data: count, % filled within max_bars after confirmation,
    average size (price and % of price). 'Filled' = price trades back through the whole zone."""
    if not len(ev):
        return {"count": 0, "pct_filled": None, "avg_size": None, "avg_size_pct": None}
    pos = {t: i for i, t in enumerate(df.index)}
    h, l, c = df["high"].to_numpy(), df["low"].to_numpy(), df["close"].to_numpy()
    filled = 0
    zone_events = 0
    for r in ev.itertuples():
        i = pos.get(r.time)
        if i is None or r.size <= 0 or r.dir == 0:
            continue
        zone_events += 1
        seg_l, seg_h = l[i + 1:i + 1 + max_bars], h[i + 1:i + 1 + max_bars]
        if r.dir == +1 and len(seg_l) and seg_l.min() <= r.bottom:
            filled += 1
        elif r.dir == -1 and len(seg_h) and seg_h.max() >= r.top:
            filled += 1
    px = ev["time"].map(lambda t: c[pos[t]] if t in pos else np.nan)
    return {"count": int(len(ev)), "pct_filled": round(100 * filled / zone_events, 1) if zone_events else None,
            "avg_size": float(ev["size"].mean()), "avg_size_pct": float((ev["size"] / px).mean() * 100)}
