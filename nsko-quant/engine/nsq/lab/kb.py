"""Knowledge Base (8.5).

A concept is stored with: a plain-English rule, the bullish and bearish condition, the code function
that detects it (name + source), stats found in the client's own data (count, % filled, average
size), three sources, the user's verdict, and a 6-step lifecycle:

  1 found      a term was seen (research TERM-CHECKER or seeded)
  2 explained  plain-English rule and bull/bear conditions written
  3 coded      a detector function exists
  4 measured   stats computed on the client's data
  5 tested     used inside a recipe and run through the Lab
  6 verdict    the user kept it, dropped it, or parked it

Sources are references to well-known published work; links are left empty where we could not
confirm a stable URL (the research SCOUT attaches links it actually found).
"""
from __future__ import annotations

import inspect
import json

import pandas as pd

from nsq.data.util import emit, ensure_table, jdump, log, now_ms

from . import detectors

LIFECYCLE = ["found", "explained", "coded", "measured", "tested", "verdict"]

_DALTON = {"title": "J. Dalton, E. Jones, R. Dalton · Mind Over Markets (Wiley, 2nd ed. 2013)", "url": None}
_STEIDL = {"title": "J. P. Steidlmayer, K. Koy · Markets and Market Logic (1986)", "url": None}
_WYCKOFF = {"title": "R. D. Wyckoff · The Richard D. Wyckoff Method of Trading and Investing in Stocks (1931)", "url": None}
_ICT = {"title": "M. J. Huddleston (ICT) · public mentorship videos on liquidity, FVGs and order blocks", "url": None}
_BROOKS = {"title": "A. Brooks · Trading Price Action: Trends (Wiley, 2011)", "url": None}
_EDWARDS = {"title": "R. Edwards, J. Magee · Technical Analysis of Stock Trends (1948)", "url": None}
_CROSBY = {"title": "T. Crabel · Day Trading with Short Term Price Patterns and Opening Range Breakout (1990)", "url": None}

CONCEPTS: dict[str, dict] = {
    "fair_value_gap": {"name": "Fair value gap", "rule": "Three candles where the first and third do not overlap: price moved so fast it left a gap that often gets revisited.",
                       "bullish": "Low of candle 3 is above the high of candle 1.", "bearish": "High of candle 3 is below the low of candle 1.",
                       "sources": [_ICT, _BROOKS, _EDWARDS]},
    "order_block": {"name": "Order block", "rule": "The last opposite-coloured candle before a strong move that breaks structure; price often reacts when it returns there.",
                    "bullish": "Last down candle before a move that breaks the last swing high.", "bearish": "Last up candle before a move that breaks the last swing low.",
                    "sources": [_ICT, _WYCKOFF, _BROOKS]},
    "liquidity_sweep": {"name": "Liquidity sweep", "rule": "Price pokes through an obvious swing high or low (where stops sit) and closes back inside: the stops were taken and the move failed.",
                        "bullish": "Wick below the last swing low, close back above it.", "bearish": "Wick above the last swing high, close back below it.",
                        "sources": [_WYCKOFF, _ICT, _DALTON]},
    "break_of_structure": {"name": "Break of structure", "rule": "A close beyond the last swing point in the direction of the trend: the trend is continuing.",
                           "bullish": "Close above the last swing high while the trend is up.", "bearish": "Close below the last swing low while the trend is down.",
                           "sources": [_EDWARDS, _BROOKS, _ICT]},
    "change_of_character": {"name": "Change of character", "rule": "The first break of structure against the trend: an early sign the trend may be turning.",
                            "bullish": "In a down trend, a close above the last swing high.", "bearish": "In an up trend, a close below the last swing low.",
                            "sources": [_WYCKOFF, _ICT, _BROOKS]},
    "displacement": {"name": "Displacement", "rule": "One unusually large, decisive candle (big body, small wicks) that shows real buying or selling pressure.",
                     "bullish": "Up candle with a body over 1.5 x ATR and at least 60 % of its range.", "bearish": "Down candle with a body over 1.5 x ATR and at least 60 % of its range.",
                     "sources": [_ICT, _BROOKS, _WYCKOFF]},
    "swing_point": {"name": "Swing high / low", "rule": "A high (low) with lower highs (higher lows) on both sides; confirmed only after the bars on the right have closed.",
                    "bullish": "Swing low: support.", "bearish": "Swing high: resistance.", "sources": [_EDWARDS, _BROOKS, _DALTON]},
    "equal_highs_lows": {"name": "Equal highs / lows", "rule": "Two swing highs (lows) at almost the same price: a pool of stop orders that price is often drawn to.",
                         "bullish": "Equal lows below price (target for sellers, then possible sweep and reverse).", "bearish": "Equal highs above price.",
                         "sources": [_ICT, _WYCKOFF, _BROOKS]},
    "inside_bar": {"name": "Inside bar", "rule": "A candle whose range sits fully inside the previous candle: a pause before expansion.",
                   "bullish": "Break above the mother bar high.", "bearish": "Break below the mother bar low.", "sources": [_BROOKS, _CROSBY, _EDWARDS]},
    "asia_range": {"name": "Asia session range", "rule": "The high and low made between 00:00 and 07:00 UTC; London often runs one side of it first.",
                   "bullish": "Sweep of the Asia low then reclaim.", "bearish": "Sweep of the Asia high then rejection.", "sources": [_CROSBY, _ICT, _DALTON]},
    "opening_range": {"name": "Opening range", "rule": "The first 30 minutes of a session; a close outside it is an opening-range breakout.",
                      "bullish": "Close above the opening-range high.", "bearish": "Close below the opening-range low.", "sources": [_CROSBY, _DALTON, _STEIDL]},
    "value_area": {"name": "Value area / POC", "rule": "Where 70 % of the session's volume traded (VAH to VAL), with the point of control at the busiest price.",
                   "bullish": "Price accepted above the prior value area high (imbalance up).", "bearish": "Price accepted below the prior value area low.",
                   "sources": [_STEIDL, _DALTON, _WYCKOFF], "code": "nsq.data.profile.from_candles"},
}


def ensure() -> None:
    from nsq.db import conn
    ensure_table(conn(), "kb_concepts", {
        "slug": "TEXT PRIMARY KEY", "name": "TEXT", "rule": "TEXT", "bullish": "TEXT", "bearish": "TEXT",
        "code_fn": "TEXT", "code_src": "TEXT", "stats_json": "TEXT", "sources_json": "TEXT",
        "verdict": "TEXT", "stage": "INTEGER DEFAULT 1", "stage_name": "TEXT", "updated_at": "INTEGER"})


def _code(slug: str) -> tuple[str | None, str | None]:
    fn = detectors.DETECTORS.get(slug)
    if fn is None:
        return CONCEPTS.get(slug, {}).get("code"), None
    return f"nsq.lab.detectors.{fn.__name__}", inspect.getsource(fn)


def seed() -> int:
    ensure()
    from nsq.db import conn
    c = conn()
    n = 0
    for slug, d in CONCEPTS.items():
        fn, src = _code(slug)
        stage = 3 if fn else 2
        cur = c.execute("INSERT OR IGNORE INTO kb_concepts (slug, name, rule, bullish, bearish, code_fn, code_src, sources_json,"
                        " stage, stage_name, updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                        (slug, d["name"], d["rule"], d["bullish"], d["bearish"], fn, src, jdump(d["sources"]), stage,
                         LIFECYCLE[stage - 1], now_ms()))
        n += cur.rowcount
    return n


def add_found(term: str, source: dict | None = None) -> str:
    """Lifecycle step 1 for a new term from research (no rule yet)."""
    ensure()
    from nsq.db import conn
    slug = term.lower().strip().replace(" ", "_").replace("-", "_")
    conn().execute("INSERT OR IGNORE INTO kb_concepts (slug, name, sources_json, stage, stage_name, updated_at) VALUES (?,?,?,?,?,?)",
                   (slug, term, jdump([source] if source else []), 1, "found", now_ms()))
    return slug


def measure(df: pd.DataFrame, slugs: list[str] | None = None) -> dict:
    """Lifecycle step 4: stats in the client's data (count, % filled, average size)."""
    ensure()
    from nsq.db import conn
    c = conn()
    out = {}
    for slug in slugs or list(detectors.DETECTORS):
        fn = detectors.DETECTORS.get(slug)
        if not fn:
            continue
        ev = fn(df)
        st = detectors.zone_stats(df, ev)
        st.update({"market": df.attrs.get("market"), "timeframe": df.attrs.get("timeframe"), "bars": len(df),
                   "synthetic": bool(df.attrs.get("synthetic")),
                   "from": df.index[0].isoformat() if len(df) else None, "to": df.index[-1].isoformat() if len(df) else None})
        out[slug] = st
        c.execute("UPDATE kb_concepts SET stats_json=?, stage=MAX(stage, 4), stage_name=CASE WHEN stage<4 THEN 'measured' ELSE stage_name END,"
                  " updated_at=? WHERE slug=?", (jdump(st), now_ms(), slug))
    log("SAVE", f"Knowledge Base measured {len(out)} concepts on {df.attrs.get('market')} {df.attrs.get('timeframe')}"
                + (" (synthetic data)" if df.attrs.get("synthetic") else ""))
    return out


def mark_tested(slug: str) -> None:
    ensure()
    from nsq.db import conn
    conn().execute("UPDATE kb_concepts SET stage=MAX(stage,5), stage_name=CASE WHEN stage<5 THEN 'tested' ELSE stage_name END,"
                   " updated_at=? WHERE slug=?", (now_ms(), slug))


def set_verdict(slug: str, verdict: str) -> dict:
    if verdict not in ("keep", "drop", "unsure"):
        raise ValueError("verdict must be keep | drop | unsure")
    ensure()
    from nsq.db import conn
    conn().execute("UPDATE kb_concepts SET verdict=?, stage=6, stage_name='verdict', updated_at=? WHERE slug=?",
                   (verdict, now_ms(), slug))
    emit("ticker_log", {"verb": "SAVE", "msg": f"Knowledge Base · {slug} → {verdict}"})
    return get(slug)


def get(slug: str) -> dict | None:
    ensure()
    from nsq.db import conn
    r = conn().execute("SELECT * FROM kb_concepts WHERE slug=?", (slug,)).fetchone()
    if r:
        r["stats"] = json.loads(r.pop("stats_json") or "null")
        r["sources"] = json.loads(r.pop("sources_json") or "[]")
        r["lifecycle"] = LIFECYCLE
    return r


def all_concepts() -> list[dict]:
    ensure()
    from nsq.db import conn
    return [get(r["slug"]) for r in conn().execute("SELECT slug FROM kb_concepts ORDER BY stage DESC, name").fetchall()]
