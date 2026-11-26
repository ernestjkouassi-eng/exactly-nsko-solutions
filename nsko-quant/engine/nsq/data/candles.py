"""`candles.get(market, timeframe, start, end) -> DataFrame` (CONTRACT.md).

Columns open, high, low, close, volume; index = UTC DatetimeIndex of bar OPEN times; closed bars
only (a bar still forming is never returned). `df.attrs` says where the data came from:
  source       broker:<name> | kraken | cache | synthetic (seeded)
  synthetic    True only for the seeded fallback
  volume_kind  exchange (real traded volume) | tick (CFD tick counts, e.g. gold) | synthetic-...
  partial      True when real data covers only part of the window asked for

Order of sources: registered broker providers -> CSV cache in <data_dir>/candles -> Kraken public
OHLC (crypto) -> seeded synthetic. Kraken's OHLC endpoint returns only the most recent 720 bars of
an interval, so long crypto history comes from `backfill_kraken_trades()` (Kraken public Trades,
paginated, about one request a second) which builds 1-minute bars into the same cache.
"""
from __future__ import annotations

import threading
import time
from pathlib import Path
from typing import Callable

import pandas as pd

from . import synthetic
from .markets import KRAKEN_INTERVALS, info, norm, pandas_rule, tf_minutes, to_utc
from .util import Blocked, cache_dir, http_json, log

KRAKEN_REST = "https://api.kraken.com/0/public"
COLS = ["open", "high", "low", "close", "volume"]

_providers: list[tuple[str, Callable]] = []
_cache_lock = threading.Lock()


def register_provider(name: str, fn: Callable[[str, str, pd.Timestamp, pd.Timestamp], pd.DataFrame | None]) -> None:
    """Brokers plug in here: fn(market, timeframe, start, end) returns closed bars or None."""
    _providers[:] = [p for p in _providers if p[0] != name] + [(name, fn)]


# ------------------------------------------------------------------------------------------- cache

def _cache_path(market: str, tf: str) -> Path:
    safe = norm(market).replace("/", "")
    return cache_dir("candles") / f"{safe}_{tf}.csv"


def read_cache(market: str, tf: str) -> pd.DataFrame:
    p = _cache_path(market, tf)
    if not p.exists():
        return pd.DataFrame(columns=COLS, index=pd.DatetimeIndex([], tz="UTC", name="time"))
    df = pd.read_csv(p)
    tcol = next((c for c in df.columns if c.lower() in ("time", "timestamp", "date", "datetime")), df.columns[0])
    df.columns = [c.lower() for c in df.columns]
    tcol = tcol.lower()
    t = df[tcol]
    idx = pd.to_datetime(t, unit="s", utc=True) if pd.api.types.is_numeric_dtype(t) else pd.to_datetime(t, utc=True)
    df = df.set_index(idx)[[c for c in COLS if c in df.columns]].astype(float)
    if "volume" not in df:
        df["volume"] = 0.0
    df.index.name = "time"
    return df[~df.index.duplicated(keep="last")].sort_index()


def write_cache(market: str, tf: str, new: pd.DataFrame) -> pd.DataFrame:
    with _cache_lock:
        old = read_cache(market, tf)
        both = pd.concat([old, new[COLS]]) if len(old) else new[COLS].copy()
        both = both[~both.index.duplicated(keep="last")].sort_index()
        out = both.copy()
        out.index = out.index.strftime("%Y-%m-%dT%H:%M:%SZ")
        out.index.name = "time"
        out.to_csv(_cache_path(market, tf))
    return both


# ------------------------------------------------------------------------------------------ kraken

def _kraken_interval(tf: str) -> int | None:
    m = tf_minutes(tf)
    for iv in sorted(KRAKEN_INTERVALS, reverse=True):
        if iv <= m and m % iv == 0:
            return iv
    return None


def fetch_kraken_ohlc(market: str, tf: str) -> pd.DataFrame | None:
    """Kraken public OHLC (GET /0/public/OHLC?pair=&interval=). Drops the still-forming last bar."""
    pair = info(market).get("kraken_rest")
    iv = _kraken_interval(tf)
    if not pair or not iv:
        return None
    data = http_json(f"{KRAKEN_REST}/OHLC", {"pair": pair, "interval": iv})
    if data.get("error"):
        raise RuntimeError("kraken: " + ";".join(data["error"]))
    res = data["result"]
    key = next(k for k in res if k != "last")
    rows = res[key][:-1]   # the last entry is the current, unclosed bar
    df = pd.DataFrame(rows, columns=["t", "open", "high", "low", "close", "vwap", "volume", "count"])
    df.index = pd.to_datetime(df["t"].astype(int), unit="s", utc=True)
    df.index.name = "time"
    df = df[COLS].astype(float)
    if iv != tf_minutes(tf):
        df = resample(df, tf, drop_incomplete=True, base_minutes=iv)
    return df


def backfill_kraken_trades(market: str, start, end=None, max_requests: int = 200) -> pd.DataFrame:
    """Build 1-minute bars from Kraken public Trades (GET /0/public/Trades?pair=&since=<ns>).
    Polite: one request per second via the shared rate limiter. Returns the bars written."""
    pair = info(market).get("kraken_rest")
    if not pair:
        raise ValueError(f"{market} is not on Kraken")
    since = int(to_utc(start).value)  # nanoseconds
    stop = to_utc(end or pd.Timestamp.utcnow()).value
    trades = []
    for _ in range(max_requests):
        data = http_json(f"{KRAKEN_REST}/Trades", {"pair": pair, "since": since})
        if data.get("error"):
            raise RuntimeError("kraken: " + ";".join(data["error"]))
        res = data["result"]
        key = next(k for k in res if k != "last")
        batch = res[key]
        if not batch:
            break
        trades.extend((float(t[2]), float(t[0]), float(t[1])) for t in batch)
        since = int(res["last"])
        if since >= stop:
            break
    if not trades:
        return pd.DataFrame(columns=COLS)
    tr = pd.DataFrame(trades, columns=["ts", "price", "qty"])
    tr.index = pd.to_datetime(tr["ts"], unit="s", utc=True)
    g = tr.resample("1min")
    bars = pd.DataFrame({"open": g["price"].first(), "high": g["price"].max(), "low": g["price"].min(),
                         "close": g["price"].last(), "volume": g["qty"].sum()}).dropna()
    bars = bars[bars.index + pd.Timedelta(minutes=1) <= tr.index.max()]  # only fully covered minutes
    bars.index.name = "time"
    write_cache(market, "1m", bars)
    log("SAVE", f"Kraken trades backfill {norm(market)} · {len(bars)} one-minute bars cached")
    return bars


# --------------------------------------------------------------------------------------- resample

def resample(df: pd.DataFrame, tf: str, drop_incomplete: bool = True, base_minutes: int | None = None) -> pd.DataFrame:
    """Aggregate to a higher timeframe. With drop_incomplete, a bucket is kept only when its last
    source bar is present (so the bucket is closed)."""
    rule = pandas_rule(tf)
    g = df.resample(rule, label="left", closed="left")
    out = pd.DataFrame({"open": g["open"].first(), "high": g["high"].max(), "low": g["low"].min(),
                        "close": g["close"].last(), "volume": g["volume"].sum()}).dropna(subset=["open"])
    if drop_incomplete and len(df):
        if base_minutes:
            base = base_minutes
        elif len(df) > 1:
            base = int(pd.Series(df.index).diff().dropna().min().total_seconds() // 60)
        else:
            base = tf_minutes(tf)
        last_src_end = df.index[-1] + pd.Timedelta(minutes=base)
        out = out[out.index + pd.Timedelta(minutes=tf_minutes(tf)) <= last_src_end]
    out.index.name = "time"
    out.attrs.update(df.attrs)
    return out


# -------------------------------------------------------------------------------------------- get

def _window(df: pd.DataFrame, s: pd.Timestamp, e: pd.Timestamp) -> pd.DataFrame:
    return df.loc[(df.index >= s) & (df.index < e)].copy()


def get(market: str, timeframe: str, start, end, *, allow_network: bool = True, min_bars: int = 1,
        prefer_synthetic: bool = False) -> pd.DataFrame:
    """Closed candles for [start, end). See module docstring for sources and attrs."""
    m = norm(market)
    s, e = to_utc(start), to_utc(end)
    now = pd.Timestamp.now(tz="UTC")
    e_eff = min(e, now)
    meta = info(m)
    vk = meta["volume_kind"]

    def _tag(df: pd.DataFrame, source: str) -> pd.DataFrame:
        df.attrs.update({"synthetic": False, "source": source, "market": m, "timeframe": timeframe,
                         "volume_kind": vk, "partial": bool(len(df) and (df.index[0] - s) > pd.Timedelta(minutes=2 * tf_minutes(timeframe)))})
        return df

    if not prefer_synthetic:
        for name, fn in list(_providers):
            try:
                df = fn(m, timeframe, s, e_eff)
                if df is not None and len(df) >= min_bars:
                    return _tag(_window(df[COLS].astype(float), s, e_eff), f"broker:{name}")
            except Exception:
                continue

        cached = read_cache(m, timeframe)
        if allow_network and meta.get("kraken_rest"):
            fresh_needed = not len(cached) or cached.index[-1] < e_eff - pd.Timedelta(minutes=2 * tf_minutes(timeframe))
            if fresh_needed:
                try:
                    kr = fetch_kraken_ohlc(m, timeframe)
                    if kr is not None and len(kr):
                        cached = write_cache(m, timeframe, kr)
                except (Blocked, RuntimeError, ValueError, OSError):
                    pass
        if not len(cached) and tf_minutes(timeframe) > 1:
            one = read_cache(m, "1m")    # bars built by a trades backfill
            if len(one):
                cached = resample(one, timeframe, drop_incomplete=True, base_minutes=1)
        win = _window(cached, s, e_eff)
        if len(win) >= min_bars:
            return _tag(win, "kraken+cache" if meta.get("kraken_rest") else "cache")

    df = synthetic.candles(m, timeframe, s, e_eff)
    return df


def latest(market: str, timeframe: str, bars: int = 500, **kw) -> pd.DataFrame:
    end = pd.Timestamp.now(tz="UTC")
    start = end - pd.Timedelta(minutes=tf_minutes(timeframe) * bars * 1.6 + 10080)
    return get(market, timeframe, start, end, **kw).tail(bars)


def refresh_loop(markets: list[str], tf: str = "1m", every_s: int = 60, stop: threading.Event | None = None) -> None:
    """Keep the cache warm and emit `candle` events for each newly closed bar (run in a thread)."""
    from .util import emit
    seen: dict[str, pd.Timestamp] = {}
    stop = stop or threading.Event()
    while not stop.is_set():
        for m in markets:
            try:
                df = latest(m, tf, bars=5)
                for t, row in df.iterrows():
                    if seen.get(m) is None or t > seen[m]:
                        seen[m] = t
                        emit("candle", {"market": m, "tf": tf, "time": t.isoformat(), **{k: float(row[k]) for k in COLS},
                                        "synthetic": bool(df.attrs.get("synthetic")), "volume_kind": df.attrs.get("volume_kind")})
            except Exception:
                pass
        stop.wait(every_s)
        time.sleep(0)
