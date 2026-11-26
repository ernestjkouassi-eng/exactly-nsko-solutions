"""News and events (8.2). Headlines and links only: no article bodies are stored or shown.

Sources (all free):
  GDELT DOC 2.0 API      api.gdeltproject.org/api/v2/doc/doc (mode=ArtList, format=json), max 1 req / 5 s
  RSS / Atom feeds       headline + link only, robots.txt checked first
  Economic calendar      econ_calendar.json (fallback rules) + settings news.calendar_file / news.events
  SEC EDGAR              current 8-K Atom feed and data.sec.gov submissions JSON (needs a User-Agent
                         that names you: setting sec.user_agent, "Name email@domain"), max 10 req / s
  US House PTRs          disclosures-clerk.house.gov yearly XML index of Periodic Transaction Reports.
                         CONTEXT ONLY, WEEKS LATE (members have up to 45 days to file). Off by default:
                         the Ethics in Government Act forbids commercial use of these reports.
  US Senate PTRs         efdsearch.senate.gov needs a terms-of-use click-through, so we only build the
                         search link; nothing is scraped.
  13F holdings           SEC 13F-HR filings for chosen managers. CONTEXT ONLY: filed up to 45 days after
                         quarter end.
"""
from __future__ import annotations

import io
import json
import zipfile
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

from .util import Blocked, emit, safe_xml, ensure_table, http_get, http_json, jdump, log, now_ms, setting

DEFAULTS = {
    "news.gdelt_enabled": True,
    "news.gdelt_queries": ['gold OR "XAU"', 'bitcoin', '"federal reserve"', 'oil tanker'],
    "news.rss_feeds": ["https://www.federalreserve.gov/feeds/press_all.xml"],
    "news.sec_enabled": True,
    "sec.user_agent": "",                # e.g. "Your Name your@email" (SEC fair-access policy)
    "news.sec_ciks": [],                 # companies to watch, e.g. [320193] for Apple
    "news.congress_enabled": False,      # off: commercial use of these reports is unlawful in the US
    "news.13f_ciks": [1067983],          # Berkshire Hathaway, as an example manager
    "news.blackout_min": 15,
}
CAL_FILE = Path(__file__).with_name("econ_calendar.json")


def ensure() -> None:
    from nsq.db import conn
    ensure_table(conn(), "news_items", {
        "id": "INTEGER PRIMARY KEY AUTOINCREMENT", "kind": "TEXT", "source": "TEXT", "title": "TEXT",
        "url": "TEXT", "published": "TEXT", "tags": "TEXT", "context_only": "INTEGER DEFAULT 0",
        "created_at": "INTEGER"}, "UNIQUE(url)")


def _store(items: list[dict]) -> int:
    ensure()
    from nsq.db import conn
    c = conn()
    n = 0
    for it in items:
        cur = c.execute("INSERT OR IGNORE INTO news_items (kind, source, title, url, published, tags, context_only, created_at)"
                        " VALUES (?,?,?,?,?,?,?,?)", (it["kind"], it["source"], it["title"][:400], it["url"],
                                                    it.get("published"), jdump(it.get("tags", [])),
                                                    int(it.get("context_only", False)), now_ms()))
        if cur.rowcount:
            n += 1
            emit("news_hit", {k: it.get(k) for k in ("kind", "source", "title", "url", "published", "tags", "context_only")})
    return n


# ------------------------------------------------------------------------------------------ GDELT

def gdelt(query: str, max_records: int = 25, timespan: str = "1d") -> list[dict]:
    data = http_json("https://api.gdeltproject.org/api/v2/doc/doc",
                     {"query": query, "mode": "ArtList", "format": "json", "maxrecords": max_records,
                      "timespan": timespan, "sort": "DateDesc"})
    return [{"kind": "news", "source": "GDELT · " + a.get("domain", ""), "title": a.get("title", ""), "url": a["url"],
             "published": a.get("seendate"), "tags": [query]} for a in data.get("articles", []) if a.get("url")]


# -------------------------------------------------------------------------------------------- RSS

def parse_feed(xml_bytes: bytes, source: str) -> list[dict]:
    """RSS 2.0 or Atom -> [{title, url, published}] (headline and link only)."""
    root = safe_xml(xml_bytes)
    out = []
    atom = "{http://www.w3.org/2005/Atom}"
    for it in root.iter("item"):
        t, l = it.findtext("title"), it.findtext("link")
        if t and l:
            out.append({"kind": "news", "source": source, "title": t.strip(), "url": l.strip(),
                        "published": it.findtext("pubDate")})
    for it in root.iter(atom + "entry"):
        t = it.findtext(atom + "title")
        link = it.find(atom + "link")
        href = link.get("href") if link is not None else None
        if t and href:
            out.append({"kind": "news", "source": source, "title": t.strip(), "url": href,
                        "published": it.findtext(atom + "updated")})
    return out


def rss(url: str) -> list[dict]:
    return parse_feed(http_get(url, check_robots=True), source=url.split("/")[2])


# ----------------------------------------------------------------------------------- calendar

def _events_from_rules(cal: dict, start: datetime, end: datetime) -> list[dict]:
    out = []
    for ev in cal.get("fixed", []):
        tz = ZoneInfo(ev.get("tz", "UTC"))
        t = datetime.fromisoformat(ev["time"]).replace(tzinfo=tz).astimezone(ZoneInfo("UTC"))
        if start <= t < end:
            out.append({**{k: v for k, v in ev.items() if k not in ("time", "tz")}, "time": t.isoformat()})
    day = start.date() - timedelta(days=1)
    while datetime.combine(day, datetime.min.time(), ZoneInfo("UTC")) < end + timedelta(days=1):
        for ev in cal.get("recurring", []):
            tz = ZoneInfo(ev.get("tz", "UTC"))
            if day.weekday() != ev["weekday"]:
                continue
            if ev["rule"] == "first_weekday" and day.day > 7:
                continue
            hh, mm = map(int, ev["time"].split(":"))
            t = datetime(day.year, day.month, day.day, hh, mm, tzinfo=tz).astimezone(ZoneInfo("UTC"))
            if start <= t < end:
                out.append({**{k: v for k, v in ev.items() if k not in ("time", "tz", "rule", "weekday")},
                            "time": t.isoformat(), "approximate": True})
        day += timedelta(days=1)
    return out


def _utc(t) -> pd.Timestamp:
    t = pd.Timestamp(t)
    return t.tz_localize("UTC") if t.tzinfo is None else t.tz_convert("UTC")


def calendar(start=None, end=None, min_impact: str = "high") -> list[dict]:
    """High-impact events between start and end (UTC). Merges the shipped fallback file, the user's
    file (news.calendar_file) and the news.events setting."""
    s = _utc(start if start is not None else pd.Timestamp.now(tz="UTC"))
    e = _utc(end) if end is not None else s + pd.Timedelta(days=14)
    start, end = s.to_pydatetime(), e.to_pydatetime()
    cals = [json.loads(CAL_FILE.read_text())]
    user_file = setting("news.calendar_file", DEFAULTS | {"news.calendar_file": ""})
    if user_file and Path(user_file).exists():
        cals.append(json.loads(Path(user_file).read_text()))
    evs = []
    for cal in cals:
        evs += _events_from_rules(cal, start, end)
    for ev in setting("news.events", {"news.events": []}) or []:
        t = _utc(ev["time"])
        if start <= t.to_pydatetime() < end:
            evs.append({**ev, "time": t.isoformat()})
    rank = {"low": 0, "medium": 1, "high": 2}
    evs = [e for e in evs if rank.get(e.get("impact", "high"), 2) >= rank[min_impact]]
    return sorted(evs, key=lambda e: e["time"])


def in_blackout(ts, minutes: int | None = None, currencies: list[str] | None = None) -> dict | None:
    """The high-impact event within +/- minutes of ts, or None."""
    minutes = minutes if minutes is not None else int(setting("news.blackout_min", DEFAULTS))
    t = _utc(ts)
    for ev in calendar(t - pd.Timedelta(minutes=minutes), t + pd.Timedelta(minutes=minutes) + pd.Timedelta(seconds=1)):
        if currencies and ev.get("currency") not in currencies:
            continue
        return ev
    return None


# ---------------------------------------------------------------------------------------- SEC

def _sec_headers() -> dict:
    ua = setting("sec.user_agent", DEFAULTS) or ""
    if not ua:
        raise PermissionError("SEC asks every client to name itself: set sec.user_agent to 'Your Name your@email'")
    return {"User-Agent": ua}


def sec_current_8k(count: int = 40) -> list[dict]:
    raw = http_get("https://www.sec.gov/cgi-bin/browse-edgar",
                   {"action": "getcurrent", "type": "8-K", "company": "", "dateb": "", "owner": "include",
                    "start": 0, "count": count, "output": "atom"}, headers=_sec_headers())
    items = parse_feed(raw, "SEC EDGAR")
    for it in items:
        it["kind"] = "filing"
    return items


def sec_company_filings(cik: int, forms: tuple[str, ...] = ("8-K", "10-Q", "10-K", "4"), limit: int = 20) -> list[dict]:
    d = http_json(f"https://data.sec.gov/submissions/CIK{int(cik):010d}.json", headers=_sec_headers())
    r = d.get("filings", {}).get("recent", {})
    out = []
    for acc, date, form, doc in zip(r.get("accessionNumber", []), r.get("filingDate", []), r.get("form", []),
                                    r.get("primaryDocument", [])):
        if form in forms:
            out.append({"kind": "filing", "source": f"SEC EDGAR · {d.get('name', cik)}", "title": f"{form} · {d.get('name', '')}",
                        "url": f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{acc.replace('-', '')}/{doc}",
                        "published": date, "tags": [form]})
        if len(out) >= limit:
            break
    return out


def thirteen_f(cik: int, limit: int = 4) -> list[dict]:
    items = sec_company_filings(cik, forms=("13F-HR", "13F-HR/A"), limit=limit)
    for it in items:
        it["kind"] = "13f"
        it["context_only"] = True
        it["title"] += " (context only: filed up to 45 days after quarter end)"
    return items


# ------------------------------------------------------------------------------------ Congress

def house_ptrs(year: int | None = None, limit: int = 50) -> list[dict]:
    """House Periodic Transaction Reports from the Clerk's yearly index (FilingType 'P')."""
    if not setting("news.congress_enabled", DEFAULTS):
        raise PermissionError("congress disclosures are off (news.congress_enabled): US law bars commercial use")
    year = year or datetime.utcnow().year
    raw = http_get(f"https://disclosures-clerk.house.gov/public_disc/financial-pdfs/{year}FD.zip", timeout=60)
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        name = next(n for n in z.namelist() if n.lower().endswith(".xml"))
        root = safe_xml(z.read(name))
    out = []
    for m in root.iter("Member"):
        if (m.findtext("FilingType") or "") != "P":
            continue
        doc = m.findtext("DocID")
        who = " ".join(x for x in (m.findtext("First"), m.findtext("Last")) if x)
        out.append({"kind": "congress", "source": "US House Clerk", "title": f"PTR · {who} ({m.findtext('StateDst')})"
                    " · context only, weeks late", "published": m.findtext("FilingDate"), "context_only": True,
                    "url": f"https://disclosures-clerk.house.gov/public_disc/ptr-pdfs/{year}/{doc}.pdf"})
    return sorted(out, key=lambda x: x["published"] or "", reverse=True)[:limit]


def senate_ptr_link() -> dict:
    return {"kind": "congress", "source": "US Senate eFD", "context_only": True,
            "title": "Senate periodic transaction reports (open and accept the site's terms yourself)",
            "url": "https://efdsearch.senate.gov/search/"}


# ---------------------------------------------------------------------------------------- run

def poll() -> dict:
    """One polite pass over every enabled source. Blocked hosts are skipped, not retried."""
    got: dict[str, int | str] = {}

    def _try(name, fn):
        try:
            items = fn()
            got[name] = _store(items)
        except (Blocked, PermissionError) as e:
            got[name] = f"skipped: {e}"
        except Exception as e:  # bad feed etc.
            got[name] = f"error: {type(e).__name__}"

    if setting("news.gdelt_enabled", DEFAULTS):
        for q in setting("news.gdelt_queries", DEFAULTS):
            _try(f"gdelt:{q}", lambda q=q: gdelt(q))
    for f in setting("news.rss_feeds", DEFAULTS):
        _try(f"rss:{f}", lambda f=f: rss(f))
    if setting("news.sec_enabled", DEFAULTS):
        _try("sec:8k", sec_current_8k)
        for cik in setting("news.sec_ciks", DEFAULTS) or []:
            _try(f"sec:{cik}", lambda cik=cik: sec_company_filings(cik))
        for cik in setting("news.13f_ciks", DEFAULTS) or []:
            _try(f"13f:{cik}", lambda cik=cik: thirteen_f(cik))
    if setting("news.congress_enabled", DEFAULTS):
        _try("house", house_ptrs)
    log("SEARCH", "news pass · " + ", ".join(f"{k}={v}" for k, v in got.items() if isinstance(v, int)))
    return got


def recent(limit: int = 100) -> list[dict]:
    ensure()
    from nsq.db import conn
    return conn().execute("SELECT * FROM news_items ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
