"""SCOUT: finds sources. Free, documented APIs only; every hit records its licence.

  GitHub    GET https://api.github.com/search/repositories?q=&sort=stars&per_page=  (10 searches/min
            unauthenticated) + GET /repos/{owner}/{repo}/readme (Accept: application/vnd.github.raw).
            Licence = the repository's own SPDX licence; we keep a short excerpt and the link only.
  arXiv     GET https://export.arxiv.org/api/query?search_query=&max_results=  (Atom; 1 request / 3 s).
            Metadata incl. abstracts is CC0; papers keep their own licence (we store the abstract + link).
  YouTube   YouTube Data API v3 search (bring-your-own key `youtube_api_key`): title + description.
            Transcripts only if the optional `youtube-transcript-api` package is installed AND setting
            research.youtube_transcripts is on (off by default: it reads YouTube's caption endpoint,
            which the YouTube Terms of Service may not allow for automated access).
  RSS       research.rss_feeds: headline + link; READER may fetch the page if robots.txt allows.
  Offline   a small built-in corpus (written for NSKO QUANT) so the pipeline runs with no network.
            Flagged synthetic=True.
"""
from __future__ import annotations

import re

from nsq.data.util import Blocked, http_get, http_json, safe_xml, secret, setting

DEFAULTS = {"research.rss_feeds": ["https://rss.arxiv.org/rss/q-fin.TR"], "research.youtube_transcripts": False,
            "research.github_per_query": 3, "research.arxiv_per_query": 3, "research.youtube_per_query": 3}

ATOM = "{http://www.w3.org/2005/Atom}"


def github(query: str, n: int | None = None) -> list[dict]:
    n = n or int(setting("research.github_per_query", DEFAULTS))
    d = http_json("https://api.github.com/search/repositories", {"q": query, "sort": "stars", "order": "desc", "per_page": n},
                  headers={"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"})
    out = []
    for it in d.get("items", [])[:n]:
        lic = (it.get("license") or {}).get("spdx_id") or "none stated (all rights reserved)"
        out.append({"kind": "GitHub", "title": it["full_name"] + (" · " + it["description"] if it.get("description") else ""),
                    "url": it["html_url"], "author": (it.get("owner") or {}).get("login"), "published": it.get("pushed_at"),
                    "licence": lic, "text": it.get("description") or "", "fetch": f"https://api.github.com/repos/{it['full_name']}/readme"})
    return out


def github_readme(api_url: str) -> str:
    raw = http_get(api_url, headers={"Accept": "application/vnd.github.raw"})
    return raw.decode("utf-8", "replace")


def arxiv(query: str, n: int | None = None) -> list[dict]:
    n = n or int(setting("research.arxiv_per_query", DEFAULTS))
    words = [w for w in re.findall(r"[A-Za-z0-9-]+", query) if len(w) > 1]
    sq = "(cat:q-fin.TR OR cat:q-fin.ST OR cat:q-fin.PM OR cat:q-fin.CP) AND (" + " AND ".join(f"all:{w}" for w in words) + ")"
    raw = http_get("https://export.arxiv.org/api/query", {"search_query": sq, "start": 0, "max_results": n,
                                                          "sortBy": "relevance"})
    root = safe_xml(raw)
    out = []
    for e in root.iter(ATOM + "entry"):
        link = next((l.get("href") for l in e.findall(ATOM + "link") if l.get("type") == "text/html"), None) or e.findtext(ATOM + "id")
        out.append({"kind": "arXiv", "title": re.sub(r"\s+", " ", e.findtext(ATOM + "title") or "").strip(), "url": link,
                    "author": ", ".join(a.findtext(ATOM + "name") or "" for a in e.findall(ATOM + "author"))[:200],
                    "published": e.findtext(ATOM + "published"), "licence": "arXiv metadata CC0; paper: author's licence",
                    "text": re.sub(r"\s+", " ", e.findtext(ATOM + "summary") or "").strip()})
    return out


def youtube(query: str, n: int | None = None) -> list[dict]:
    key = secret("youtube_api_key")
    if not key:
        raise PermissionError("YouTube needs your own free YouTube Data API key (youtube_api_key)")
    n = n or int(setting("research.youtube_per_query", DEFAULTS))
    d = http_json("https://www.googleapis.com/youtube/v3/search",
                  {"part": "snippet", "q": query, "type": "video", "maxResults": n, "key": key})
    out = []
    for it in d.get("items", []):
        vid = it["id"].get("videoId")
        sn = it.get("snippet", {})
        text = sn.get("description", "")
        if setting("research.youtube_transcripts", DEFAULTS):
            text = transcript(vid) or text
        out.append({"kind": "YouTube", "title": sn.get("title", ""), "url": f"https://www.youtube.com/watch?v={vid}",
                    "author": sn.get("channelTitle"), "published": sn.get("publishedAt"),
                    "licence": "YouTube standard licence (watch/link only)", "text": text})
    return out


def transcript(video_id: str) -> str | None:
    try:
        from youtube_transcript_api import YouTubeTranscriptApi  # MIT; optional
    except ImportError:
        return None
    try:
        api = YouTubeTranscriptApi()
        parts = api.fetch(video_id) if hasattr(api, "fetch") else YouTubeTranscriptApi.get_transcript(video_id)
        return " ".join(getattr(p, "text", None) or p.get("text", "") for p in parts)
    except Exception:
        return None


def rss(url: str) -> list[dict]:
    from nsq.data.news import parse_feed
    items = parse_feed(http_get(url, check_robots=True), url.split("/")[2])
    return [{"kind": "Web", "title": i["title"], "url": i["url"], "published": i.get("published"),
             "licence": "publisher's copyright (headline + link only)", "text": "", "fetch": i["url"]} for i in items[:5]]


# ---------------------------------------------------------------------------------- offline corpus

OFFLINE: list[dict] = [
    {"title": "Time-series momentum on gold, explained", "text": "Time-series momentum buys a market whose own past return is positive and sells it when negative. On gold, a 20 and 50 bar moving average cross is a simple trend following filter. Use an ATR stop so the position size adapts to volatility. Trend following loses in ranges, so expect many small losses and a few large wins."},
    {"title": "Reading the volume profile like a market maker", "text": "The volume profile shows where trading happened. The point of control is the busiest price and the value area holds 70 percent of the volume. When price is inside the prior value area the market is balanced and tends to rotate from value area high to value area low. A low volume node is a thin area that price crosses fast. Order flow traders wait for a liquidity sweep of the value area low and a reclaim before buying."},
    {"title": "Opening-range breakout: does it still work?", "text": "The opening range is the high and low of the first 30 minutes of the session. A breakout trader buys a close above the opening range high with a stop at the middle of the range. On gold the London open is the natural session for an opening range breakout. Consolidation before the open often leads to a squeeze."},
    {"title": "VWAP reversion intraday", "text": "Price that stretches two standard deviations from the session VWAP often reverts toward it. This mean reversion idea fades the stretch and targets VWAP, with a stop beyond the extreme. It works best in balanced, range-bound sessions and fails on strong trend days."},
    {"title": "Order blocks and fair value gaps", "text": "A fair value gap is a three candle imbalance where candle three does not overlap candle one. An order block is the last opposite candle before a displacement that causes a break of structure. Price often returns to fill the gap or test the order block. A change of character warns that the trend may be turning. A breaker block is a failed order block."},
    {"title": "Seasonality in precious metals", "text": "Gold has shown calendar effects: some months and the turn of the month have been stronger on average. Seasonality is weak on its own and should be combined with a trend or volatility filter. Day of week effects are small after costs."},
    {"title": "Carry and roll yield in commodity futures", "text": "Carry is the return from holding a position as the futures curve rolls. In backwardation the roll yield is positive; in contango it is negative. In crypto the funding rate of perpetual swaps plays the same role as carry."},
    {"title": "This strategy always wins", "text": "Our secret indicator always wins and gives a guaranteed 5% a day. Never lose again."},
]


def offline(query: str) -> list[dict]:
    q = set(query.lower().split())
    scored = sorted(OFFLINE, key=lambda d: -len(q & set((d["title"] + " " + d["text"]).lower().split())))
    return [{"kind": "Offline", "title": d["title"], "url": f"offline://nsko/{i}-{re.sub(r'[^a-z0-9]+', '-', d['title'].lower())}",
             "author": "NSKO QUANT built-in notes", "published": None, "licence": "NSKO Solutions (built-in)",
             "text": d["text"], "synthetic": True} for i, d in enumerate(scored[:3])]


SOURCES = {"GitHub": github, "arXiv": arxiv, "YouTube": youtube}


def search(kind: str, query: str) -> tuple[list[dict], str | None]:
    """Returns (hits, reason-if-skipped)."""
    try:
        return SOURCES[kind](query), None
    except (Blocked, PermissionError) as e:
        return [], str(e)
    except Exception as e:
        return [], f"{type(e).__name__}: {e}"[:200]
