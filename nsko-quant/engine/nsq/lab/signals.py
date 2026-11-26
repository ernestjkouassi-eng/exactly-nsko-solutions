"""`signals.generate(recipe, candles) -> list[dict]` (CONTRACT.md).

Each signal: {"time", "side": "buy"|"sell", "entry", "stop", "target", "reason"}.
CLOSED BARS ONLY: a signal stamped at bar t uses data up to and including bar t (its close), never
t+1. `time` is bar t's open time (the candle index); the backtester fills at bar t+1's open.
Every generator below is tested for this: appending future bars never changes earlier signals.

Generators (recipe["entry"]["type"]):
  ema_cross        trend follower: fast/slow EMA cross, ATR stop, R-multiple target
  orb              opening-range breakout: first N minutes of a session, break on a close
  vwap_reversion   mean reversion to session VWAP: stretch of k std-devs, target = VWAP
  nsko_of_1        NSKO-OF-1 "react, don't predict" order-flow recipe (9.3), see `_nsko_of_1`
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from nsq.data.markets import info, tf_minutes

from . import levels as lv
from .indicators import atr, ema, in_sessions, rolling_median, session_key, session_offset, session_vwap


def _p(recipe: dict, key: str, default):
    return recipe.get("params", {}).get(key, recipe.get("entry", {}).get(key, default))


def _blackout_mask(index: pd.DatetimeIndex, minutes: int, market: str) -> np.ndarray:
    if not minutes or not len(index):
        return np.zeros(len(index), dtype=bool)
    try:
        from nsq.data.news import calendar
        evs = calendar(index[0] - pd.Timedelta(days=1), index[-1] + pd.Timedelta(days=1))
    except Exception:
        return np.zeros(len(index), dtype=bool)
    m = np.zeros(len(index), dtype=bool)
    ns = index.as_unit("ns").asi8
    w = minutes * 60 * 1_000_000_000
    for ev in evs:
        t = pd.Timestamp(ev["time"]).value
        lo, hi = np.searchsorted(ns, t - w), np.searchsorted(ns, t + w, side="right")
        m[lo:hi] = True
    return m


def _filters(recipe: dict, df: pd.DataFrame) -> np.ndarray:
    f = recipe.get("filters", {}) or {}
    ok = in_sessions(df.index, f.get("session"))
    if f.get("news_blackout_min") and _p(recipe, "apply_news", True):
        ok &= ~_blackout_mask(df.index, int(f["news_blackout_min"]), recipe.get("market", ""))
    return ok


def _stop_target(recipe: dict, side: int, entry: float, a: float, swing_px: float | None = None,
                 level_stop: float | None = None, level_target: float | None = None) -> tuple[float, float] | None:
    st = recipe.get("stop", {"type": "atr", "mult": 1.0})
    tg = recipe.get("target", {"type": "r", "r": 1.6})
    mult = float(st.get("mult", 1.0))
    if st.get("type") == "level" and level_stop is not None:
        stop = level_stop
    elif st.get("type") == "swing" and swing_px is not None:
        stop = swing_px - side * mult * 0.1 * a
    else:
        stop = entry - side * mult * a
    risk = (entry - stop) * side
    if not np.isfinite(risk) or risk <= 0:
        return None
    if tg.get("type") == "level" and level_target is not None and (level_target - entry) * side > 0:
        target = level_target
    else:
        target = entry + side * float(tg.get("r", 1.6)) * risk
    return float(stop), float(target)


def _sig(t, side: int, entry, stop, target, reason: str) -> dict:
    return {"time": t.isoformat(), "side": "buy" if side > 0 else "sell", "entry": float(entry),
            "stop": float(stop), "target": float(target), "reason": reason}


# --------------------------------------------------------------------------------- trend follower

def _ema_cross(recipe: dict, df: pd.DataFrame) -> list[dict]:
    fast, slow = int(_p(recipe, "fast", 20)), int(_p(recipe, "slow", 50))
    a = atr(df, int(_p(recipe, "atr_n", 14))).to_numpy()
    c = df["close"]
    ef, es = ema(c, fast).to_numpy(), ema(c, slow).to_numpy()
    diff = ef - es
    ok = _filters(recipe, df)
    swing_n = int(_p(recipe, "swing_lookback", 10))
    lows = df["low"].rolling(swing_n, min_periods=1).min().to_numpy()
    highs = df["high"].rolling(swing_n, min_periods=1).max().to_numpy()
    out = []
    cv = c.to_numpy()
    for i in range(1, len(df)):
        if not (np.isfinite(diff[i]) and np.isfinite(diff[i - 1]) and np.isfinite(a[i])) or not ok[i]:
            continue
        side = 1 if diff[i - 1] <= 0 < diff[i] else (-1 if diff[i - 1] >= 0 > diff[i] else 0)
        if not side:
            continue
        st = _stop_target(recipe, side, cv[i], a[i], swing_px=lows[i] if side > 0 else highs[i])
        if st:
            out.append(_sig(df.index[i], side, cv[i], *st, f"EMA {fast}/{slow} cross {'up' if side > 0 else 'down'}"))
    return out


# ---------------------------------------------------------------------------- opening-range breakout

def _orb(recipe: dict, df: pd.DataFrame) -> list[dict]:
    open_h = float(_p(recipe, "open_hour", 7.0))
    minutes = int(_p(recipe, "range_minutes", 30))
    last_h = float(_p(recipe, "last_entry_hour", open_h + 5))
    bar_m = tf_minutes(recipe.get("timeframe", "15m"))
    a = atr(df, int(_p(recipe, "atr_n", 14))).to_numpy()
    ok = _filters(recipe, df)
    h = df.index.hour.values + df.index.minute.values / 60.0
    day = df.index.normalize().as_unit("ns").asi8
    H, L, C = df["high"].to_numpy(), df["low"].to_numpy(), df["close"].to_numpy()
    out = []
    cur_day, rh, rl, done = None, -np.inf, np.inf, set()
    range_end = open_h + minutes / 60.0
    for i in range(len(df)):
        if day[i] != cur_day:
            cur_day, rh, rl, done = day[i], -np.inf, np.inf, set()
        # bar i belongs to the range if it opens inside the range window
        if open_h <= h[i] < range_end:
            rh, rl = max(rh, H[i]), min(rl, L[i])
            continue
        complete = h[i] >= range_end and h[i] - bar_m / 60.0 < last_h and np.isfinite(rh)
        if not complete or not ok[i] or not np.isfinite(a[i]):
            continue
        for side, cond, lvl in ((1, C[i] > rh, rh), (-1, C[i] < rl, rl)):
            if cond and side not in done:
                done.add(side)
                mid = (rh + rl) / 2
                st = _stop_target(recipe, side, C[i], a[i], swing_px=rl if side > 0 else rh, level_stop=mid)
                if st:
                    out.append(_sig(df.index[i], side, C[i], *st,
                                    f"opening range {rl:.2f}-{rh:.2f} broken {'up' if side > 0 else 'down'}"))
    return out


# -------------------------------------------------------------------------- VWAP mean reversion

def _vwap_reversion(recipe: dict, df: pd.DataFrame) -> list[dict]:
    k = float(_p(recipe, "k", 2.0))
    n = int(_p(recipe, "dev_n", 50))
    off = session_offset(recipe.get("market", ""))
    vw = session_vwap(df, off)
    dev = df["close"] - vw
    sd = dev.rolling(n, min_periods=n).std().to_numpy()
    a = atr(df, int(_p(recipe, "atr_n", 14))).to_numpy()
    ok = _filters(recipe, df)
    key = session_key(df.index, off)
    bar_in_session = pd.Series(1, index=df.index).groupby(key).cumsum().to_numpy()
    min_bars = int(_p(recipe, "min_session_bars", 4))
    d = dev.to_numpy()
    C, V = df["close"].to_numpy(), vw.to_numpy()
    out = []
    for i in range(1, len(df)):
        if not ok[i] or bar_in_session[i] < min_bars or not (np.isfinite(sd[i]) and sd[i] > 0 and np.isfinite(a[i])):
            continue
        z, zp = d[i] / sd[i], d[i - 1] / sd[i - 1] if np.isfinite(sd[i - 1]) and sd[i - 1] > 0 else 0.0
        side = 1 if (z < -k and zp >= -k) else (-1 if (z > k and zp <= k) else 0)
        if not side:
            continue
        st = _stop_target(recipe, side, C[i], a[i], level_target=V[i])
        if st:
            out.append(_sig(df.index[i], side, C[i], *st, f"{abs(z):.1f} sd from session VWAP {V[i]:.2f}"))
    return out


# ------------------------------------------------------------------------------------ NSKO-OF-1

def _nsko_of_1(recipe: dict, df: pd.DataFrame) -> list[dict]:
    """React, don't predict.
    1. Map levels first (prior-session VAH/VAL/POC/LVN, prior session high/low, HTF fair value gaps).
    2. Classify the state: balanced (inside prior value) or imbalanced (accepted outside it).
    3. Act only AT a mapped level (within tol x ATR).
    4. Confirm: a sweep-and-reclaim of the level, or aggressive volume at it (volume spike with the
       close in the trade direction's part of the bar).
    5. Stop just beyond the swept extreme; target the next profile level / POC (else R multiple).
    Timeframes: candles are the LOWER timeframe (3m or 5m); levels come from `htf` (15m or 1h).
    Session: London + NY for gold; 24/7 with a liquidity filter for crypto."""
    market = recipe.get("market", "")
    ltf_m = tf_minutes(recipe.get("timeframe", "3m"))
    htf = _p(recipe, "htf", "15m")
    tol = float(_p(recipe, "level_tol_atr", 0.25))
    eps = float(_p(recipe, "sweep_eps_atr", 0.05))
    vol_mult = float(_p(recipe, "vol_mult", 1.8))
    buf = float(_p(recipe, "stop_buf_atr", 0.15))
    min_rr = float(_p(recipe, "min_rr", 1.2))
    max_per_session = int(_p(recipe, "max_per_session", 3))
    accept = int(_p(recipe, "accept_bars", 3))
    liq_frac = float(_p(recipe, "liquidity_frac", 0.6))
    a = atr(df, int(_p(recipe, "atr_n", 14))).to_numpy()
    off = session_offset(market)
    L = lv.prior_session_levels(df, off, bins=int(_p(recipe, "profile_bins", 40)))
    poc, vah, val = (L[x].to_numpy(dtype=float) for x in ("poc", "vah", "val"))
    psh, psl = L["psh"].to_numpy(dtype=float), L["psl"].to_numpy(dtype=float)
    lvns = L["lvn"].to_numpy()
    O, H, Lo, C, V = (df[x].to_numpy(dtype=float) for x in ("open", "high", "low", "close", "volume"))
    state = lv.market_state(C, vah, val, accept)
    vmed = rolling_median(df["volume"], int(_p(recipe, "vol_n", 50))).shift(1).to_numpy()
    ok = _filters(recipe, df)
    if info(market).get("kind") == "crypto" or not (recipe.get("filters") or {}).get("session"):
        day_bars = max(10, int(1440 / ltf_m))
        vday = df["volume"].rolling(20, min_periods=5).mean().to_numpy()
        vlong = rolling_median(df["volume"], 7 * day_bars).shift(1).to_numpy()
        ok &= ~(np.isfinite(vlong) & (vday < liq_frac * vlong))   # thin market: stand aside

    fv = lv.htf_fvgs(df, htf, ltf_m) if _p(recipe, "use_fvg", True) else None
    fv_list = [] if fv is None else list(fv.itertuples())
    fv_ptr, live_fvgs = 0, []
    ns = df.index.as_unit("ns").asi8
    key = session_key(df.index, off)
    per_session: dict[int, int] = {}
    used: set[tuple[int, float, int]] = set()
    out = []
    for i in range(len(df)):
        # activate FVGs that are known by the close of bar i, then drop filled ones
        while fv_ptr < len(fv_list) and fv_list[fv_ptr].avail.value <= ns[i]:
            g = fv_list[fv_ptr]
            live_fvgs.append([g.dir, g.top, g.bottom])
            fv_ptr += 1
        if live_fvgs:
            live_fvgs = [g for g in live_fvgs if not ((g[0] > 0 and Lo[i] <= g[2]) or (g[0] < 0 and H[i] >= g[1]))]
            live_fvgs = live_fvgs[-20:]
        if not ok[i] or not np.isfinite(a[i]) or not np.isfinite(poc[i]) or a[i] <= 0:
            continue
        if per_session.get(key[i], 0) >= max_per_session:
            continue
        st = state[i]
        # 1) level map for this bar, by side
        longs: list[tuple[str, float]] = []
        shorts: list[tuple[str, float]] = []
        if st == 0:
            longs += [("VAL", val[i]), ("prior session low", psl[i])]
            shorts += [("VAH", vah[i]), ("prior session high", psh[i])]
            for x in (lvns[i] or ()):
                (longs if x < poc[i] else shorts).append(("LVN", x))
        elif st > 0:
            longs += [("VAH retest", vah[i]), ("prior session high retest", psh[i])]
            shorts += [("prior session high", psh[i])] if C[i] < psh[i] else []
        else:
            shorts += [("VAL retest", val[i]), ("prior session low retest", psl[i])]
            longs += [("prior session low", psl[i])] if C[i] > psl[i] else []
        for d, top, bot in live_fvgs:
            if d > 0:
                longs.append(("bullish FVG", top))
            else:
                shorts.append(("bearish FVG", bot))
        rng = max(H[i] - Lo[i], 1e-12)
        vol_spike = np.isfinite(vmed[i]) and vmed[i] > 0 and V[i] >= vol_mult * vmed[i]
        done = False
        for side, cands in ((1, longs), (-1, shorts)):
            for name, lvl in cands:
                if not np.isfinite(lvl) or done:
                    continue
                if side > 0:
                    at_level = Lo[i] <= lvl + tol * a[i] and C[i] > lvl
                    sweep = Lo[i] < lvl - eps * a[i] and C[i] > lvl
                    aggr = vol_spike and (C[i] - Lo[i]) / rng >= 0.6 and C[i] > O[i]
                else:
                    at_level = H[i] >= lvl - tol * a[i] and C[i] < lvl
                    sweep = H[i] > lvl + eps * a[i] and C[i] < lvl
                    aggr = vol_spike and (H[i] - C[i]) / rng >= 0.6 and C[i] < O[i]
                if not at_level or not (sweep or aggr):
                    continue
                tag = (int(key[i]), round(float(lvl), 6), side)
                if tag in used:
                    continue
                extreme = Lo[i] if side > 0 else H[i]
                stop = min(extreme, lvl) - buf * a[i] if side > 0 else max(extreme, lvl) + buf * a[i]
                entry = C[i]
                risk = (entry - stop) * side
                if risk <= 0:
                    continue
                # target: next profile level beyond entry in the trade direction
                pool = [poc[i], vah[i], val[i], psh[i], psl[i], *(lvns[i] or ())]
                ahead = sorted([p for p in pool if np.isfinite(p) and (p - entry) * side > 0.25 * risk],
                               key=lambda p: (p - entry) * side)
                tgt = ahead[0] if ahead else None
                if st == 0 and np.isfinite(poc[i]) and (poc[i] - entry) * side > 0.25 * risk:
                    tgt = poc[i]                    # balanced: rotate back to POC
                rr_r = float(_p(recipe, "fallback_r", 2.0))
                if tgt is None or (tgt - entry) * side / risk < min_rr:
                    tgt = entry + side * max(min_rr, rr_r) * risk
                state_txt = "balanced" if st == 0 else ("imbalanced up" if st > 0 else "imbalanced down")
                how = "sweep and reclaim" if sweep else "aggressive volume"
                out.append(_sig(df.index[i], side, entry, stop, tgt,
                                f"NSKO-OF-1 · {state_txt} · {name} {lvl:.2f} · {how}"))
                used.add(tag)
                per_session[key[i]] = per_session.get(key[i], 0) + 1
                done = True
            if done:
                break
    return out


GENERATORS = {"ema_cross": _ema_cross, "trend": _ema_cross, "orb": _orb, "breakout": _orb,
              "vwap_reversion": _vwap_reversion, "mean_reversion": _vwap_reversion, "nsko_of_1": _nsko_of_1}
IDEA_DEFAULT = {"Trend following": "ema_cross", "Breakout": "orb", "Mean reversion": "vwap_reversion",
                "Orderflow": "nsko_of_1", "Volatility": "orb", "Seasonality": "ema_cross", "Carry": "ema_cross"}


def generator_for(recipe: dict) -> str:
    t = (recipe.get("entry") or {}).get("type") or IDEA_DEFAULT.get(recipe.get("idea_type", ""), "ema_cross")
    if t not in GENERATORS:
        raise ValueError(f"unknown entry type {t!r}; known: {sorted(GENERATORS)}")
    return t


def generate(recipe: dict, candles: pd.DataFrame) -> list[dict]:
    """Signals for `recipe` on closed `candles`. Pure: no I/O, no randomness."""
    if candles is None or len(candles) < 3:
        return []
    df = candles[["open", "high", "low", "close", "volume"]].astype(float)
    df.attrs.update(candles.attrs)
    return GENERATORS[generator_for(recipe)](recipe, df)
