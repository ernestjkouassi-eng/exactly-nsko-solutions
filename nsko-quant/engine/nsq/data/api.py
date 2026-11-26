"""FastAPI router for market data. Mount with `app.include_router(nsq.data.api.router)`."""
from __future__ import annotations

import pandas as pd
from fastapi import APIRouter, HTTPException

from . import candles, news, profile
from .markets import MARKETS, tf_minutes
from .util import host_status

router = APIRouter(prefix="/data", tags=["data"])


@router.get("/markets")
def markets() -> dict:
    return {"markets": [{"market": k, **{kk: v[kk] for kk in ("kind", "volume_kind", "sessions")}} for k, v in MARKETS.items()]}


@router.get("/candles")
def get_candles(market: str, tf: str = "15m", bars: int = 500, start: str | None = None, end: str | None = None) -> dict:
    try:
        tf_minutes(tf)
    except ValueError as e:
        raise HTTPException(400, str(e))
    bars = max(1, min(bars, 20000))
    if start:
        df = candles.get(market, tf, start, end or pd.Timestamp.now(tz="UTC")).tail(bars)
    else:
        df = candles.latest(market, tf, bars)
    return {"attrs": {k: (bool(v) if k in ("synthetic", "partial") else v) for k, v in df.attrs.items()},
            "candles": [{"time": int(t.timestamp()), **{c: float(r[c]) for c in candles.COLS}} for t, r in df.iterrows()]}


@router.get("/profile")
def get_profile(market: str, tf: str = "15m", bars: int = 96, bins: int = 48) -> dict:
    df = candles.latest(market, tf, bars)
    pr = profile.from_candles(df, bins=bins)
    pr["synthetic"] = bool(df.attrs.get("synthetic"))
    return pr


@router.get("/news")
def get_news(limit: int = 100) -> dict:
    return {"items": news.recent(limit)}


@router.post("/news/poll")
def poll_news() -> dict:
    return news.poll()


@router.get("/calendar")
def get_calendar(days: int = 14, impact: str = "high") -> dict:
    now = pd.Timestamp.now(tz="UTC")
    return {"events": news.calendar(now, now + pd.Timedelta(days=days), impact)}


@router.get("/hosts")
def hosts() -> dict:
    return host_status()
