"""News / events blackout: no new entries within ±N minutes (default 15) of a high-impact event.

Calendar source for now: the `news.events` setting and/or a JSON file named in `news.calendar_file`
(a list of {"time": ISO-8601 UTC, "impact": "high"|"medium"|"low", "title", "currency"}).
"""
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

from ..settings import get

# Which currencies / themes move which market.
MARKET_CCY = {"XAU/USD": {"USD", "XAU"}, "BTC/USD": {"USD", "BTC", "CRYPTO"}, "ETH/USD": {"USD", "ETH", "CRYPTO"},
              "EUR/USD": {"EUR", "USD"}, "NVDA": {"USD", "NVDA"}, "AAPL": {"USD", "AAPL"}}


def _parse(t: str) -> dt.datetime:
    d = dt.datetime.fromisoformat(t.replace("Z", "+00:00"))
    return d if d.tzinfo else d.replace(tzinfo=dt.timezone.utc)


def events(at: dt.datetime | None = None) -> list[dict]:
    out = list(get("news.events") or [])
    if get("news.use_data_calendar", True):
        try:  # the shipped fallback calendar from nsq.data.news (other module, imported lazily)
            from ..data import news as data_news
            at = at or dt.datetime.now(dt.timezone.utc)
            out += data_news.calendar(at - dt.timedelta(days=1), at + dt.timedelta(days=1))
        except Exception:
            pass
    f = get("news.calendar_file")
    if f and Path(f).exists():
        try:
            out += json.loads(Path(f).read_text())
        except Exception:
            pass
    return out


def check(market: str, at: dt.datetime | None = None, blackout_min: float | None = None) -> dict:
    at = at or dt.datetime.now(dt.timezone.utc)
    win = dt.timedelta(minutes=float(blackout_min if blackout_min is not None else get("news.blackout_min")))
    ccys = MARKET_CCY.get(market, {"USD"})
    hits = []
    seen = set()
    for e in events(at):
        if str(e.get("impact", "high")).lower() != "high":
            continue
        cur = str(e.get("currency", "USD")).upper()
        if cur not in ccys and cur != "ALL":
            continue
        try:
            t = _parse(e["time"])
        except Exception:
            continue
        if abs(t - at) <= win and (e.get("title"), t) not in seen:
            seen.add((e.get("title"), t))
            hits.append({"title": e.get("title", "event"), "time": t.isoformat(), "currency": cur,
                         "minutes_away": round((t - at).total_seconds() / 60, 1)})
    return {"market": market, "blackout": bool(hits), "events": hits, "window_min": win.total_seconds() / 60,
            "source": "news.events setting, news.calendar_file and the shipped calendar"}
