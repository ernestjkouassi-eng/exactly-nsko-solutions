"""JARVIS research team (8.3).

  JARVIS        plans the round (queries) and watches the budget
  SCOUT         searches GitHub, arXiv, YouTube (own key), RSS; offline corpus when nothing is reachable
  READER        fetches and extracts text (robots.txt respected for web pages)
  WATCHER       highlights trading terms in the text, rejects hype ("always wins", "guaranteed")
  SUMMARISER 1-3  summary + idea type (Trend following, Mean reversion, Breakout, Volatility,
                Orderflow, Seasonality, Carry): local Ollama model, else deterministic offline
  TERM-CHECKER  queues terms the Knowledge Base does not have yet
  RECIPE-MAKER  turns an idea into recipe JSON (CONTRACT.md) for the Lab

Every action emits ticker_log / agent_status / agent_handoff / source_added / summary_done /
term_found / recipe_created, and a budget_update. Results go to the sources, summaries, terms and
recipes tables. The daily compute budget (research.daily_budget, in "think units") stops a round
when it runs out: 1 unit ~ 1,000 tokens of local model work; offline steps cost 0.05.
"""
from __future__ import annotations

import calendar as _cal
import html
import re
from datetime import date, datetime, timezone
from html.parser import HTMLParser

from nsq.data.util import Blocked, audit_safe, emit, ensure_table, http_get, jdump, log, now_ms, setting

from . import lexicon, llm, scout

DEFAULTS = {
    "research.daily_budget": 50.0,
    "research.queries": ['orderflow volume profile backtest', 'time-series momentum gold', 'opening range breakout',
                         'VWAP mean reversion intraday', 'liquidity sweep reclaim'],
    "research.kinds": ["GitHub", "arXiv", "YouTube"],
    "research.max_sources_per_round": 12,
    "research.auto_recipe": True,
}
AGENTS = ["JARVIS", "SCOUT", "READER", "WATCHER", "SUMMARISER 1", "SUMMARISER 2", "SUMMARISER 3", "TERM-CHECKER", "RECIPE-MAKER"]
COST = {"search": 0.05, "read": 0.05, "offline": 0.05, "llm_per_1k_tokens": 1.0}


# ----------------------------------------------------------------------------------------- db

def ensure() -> None:
    from nsq.db import conn
    c = conn()
    ensure_table(c, "sources", {"id": "INTEGER PRIMARY KEY AUTOINCREMENT", "kind": "TEXT", "title": "TEXT", "url": "TEXT",
                                "author": "TEXT", "published": "TEXT", "licence": "TEXT", "excerpt": "TEXT",
                                "highlights_json": "TEXT", "idea_type": "TEXT", "status": "TEXT", "reject_reason": "TEXT",
                                "synthetic": "INTEGER DEFAULT 0", "query": "TEXT", "created_at": "INTEGER"}, "UNIQUE(url)")
    ensure_table(c, "summaries", {"id": "INTEGER PRIMARY KEY AUTOINCREMENT", "source_id": "INTEGER", "agent": "TEXT",
                                  "summary": "TEXT", "idea_type": "TEXT", "confidence": "REAL", "model": "TEXT",
                                  "created_at": "INTEGER"})
    ensure_table(c, "terms", {"id": "INTEGER PRIMARY KEY AUTOINCREMENT", "term": "TEXT", "status": "TEXT",
                              "first_source_id": "INTEGER", "seen": "INTEGER DEFAULT 1", "created_at": "INTEGER"}, "UNIQUE(term)")
    ensure_table(c, "research_budget", {"day": "TEXT PRIMARY KEY", "used": "REAL", "updated_at": "INTEGER"})


# ------------------------------------------------------------------------------------- budget

class Budget:
    def __init__(self):
        ensure()
        self.of = float(setting("research.daily_budget", DEFAULTS))
        self.day = date.today().isoformat()

    @property
    def used(self) -> float:
        from nsq.db import conn
        r = conn().execute("SELECT used FROM research_budget WHERE day=?", (self.day,)).fetchone()
        return float(r["used"]) if r else 0.0

    def left(self) -> float:
        return self.of - self.used

    def spend(self, units: float, what: str = "") -> bool:
        from nsq.db import conn
        if self.used + units > self.of:
            log("PAUSE", f"think budget used up ({self.used:.2f} of {self.of:.0f}) · research paused until tomorrow")
            emit("agent_status", {"agent": "JARVIS", "status": "paused", "item": "daily budget reached"})
            self.emit()
            return False
        conn().execute("INSERT INTO research_budget (day, used, updated_at) VALUES (?,?,?) ON CONFLICT(day) DO UPDATE "
                       "SET used=used+excluded.used, updated_at=excluded.updated_at", (self.day, units, now_ms()))
        return True

    def emit(self) -> dict:
        d = date.today()
        left_days = _cal.monthrange(d.year, d.month)[1] - d.day
        p = {"used": round(self.used, 3), "of": self.of, "day": self.day, "days": left_days, "mode": llm.mode()}
        emit("budget_update", p)
        return p


# ------------------------------------------------------------------------------------- reader

class _Text(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts, self._skip = [], 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "nav", "footer", "noscript"):
            self._skip += 1

    def handle_endtag(self, tag):
        if tag in ("script", "style", "nav", "footer", "noscript") and self._skip:
            self._skip -= 1

    def handle_data(self, data):
        if not self._skip:
            self.parts.append(data)


def extract_text(raw: str) -> str:
    if "<" in raw and ">" in raw and re.search(r"<(html|body|p|div)\b", raw, re.I):
        p = _Text()
        p.feed(raw)
        raw = " ".join(p.parts)
    raw = re.sub(r"!\[[^\]]*\]\([^)]*\)|\[([^\]]*)\]\([^)]*\)", r"\1", raw)   # markdown links/images
    raw = re.sub(r"[#*`>|_]{1,}", " ", raw)
    return re.sub(r"\s+", " ", html.unescape(raw)).strip()


def read(hit: dict) -> str:
    text = hit.get("text") or ""
    url = hit.get("fetch")
    if not url:
        return text
    try:
        if "api.github.com" in url:
            body = scout.github_readme(url)
        else:
            body = http_get(url, check_robots=True).decode("utf-8", "replace")
        return (text + " " + extract_text(body))[:20000]
    except (Blocked, PermissionError, Exception):
        return text


def highlight(text: str) -> list[str]:
    return lexicon.find_terms(text)


# ---------------------------------------------------------------------------------- recipes

TF_RE = re.compile(r"\b(1|3|5|15|30)\s?(?:m|min|minute)s?\b|\b(1|4)\s?(?:h|hour)s?\b|\b(daily|1d)\b", re.I)


def _guess_market(text: str) -> str:
    t = text.lower()
    if any(w in t for w in ("gold", "xau", "precious metal")):
        return "XAU/USD"
    if any(w in t for w in ("bitcoin", "btc", "crypto")):
        return "BTC/USD"
    if any(w in t for w in ("ether", "eth ")):
        return "ETH/USD"
    return "XAU/USD"


def _guess_tf(text: str, idea: str) -> str:
    m = TF_RE.search(text)
    if m:
        if m.group(1):
            return f"{m.group(1)}m"
        if m.group(2):
            return f"{m.group(2)}h"
        return "1d"
    return {"Orderflow": "3m", "Breakout": "15m", "Mean reversion": "15m"}.get(idea, "1h")


def make_recipe(source_id: int, title: str, text: str, idea: str) -> dict:
    from nsq.lab.seed import PACK
    market = _guess_market(title + " " + text)
    tf = _guess_tf(title + " " + text, idea)
    gen = {"Trend following": "ema_cross", "Mean reversion": "vwap_reversion", "Breakout": "orb",
           "Volatility": "orb", "Orderflow": "nsko_of_1", "Seasonality": "ema_cross", "Carry": "ema_cross"}[idea]
    template = next((p for p in PACK if p["entry"]["type"] == gen and p["market"] == market), None) or \
        next(p for p in PACK if p["entry"]["type"] == gen)
    if gen == "nsko_of_1":
        tf = "3m" if market == "XAU/USD" else "5m"
    short = market.split("/")[0]
    rid = f"src{source_id}-{gen}-{short.lower()}-{tf}"
    rec = {"id": rid, "name": f"{idea.split()[0]}-{short} #{source_id}", "market": market, "timeframe": tf, "idea_type": idea,
           "entry": dict(template["entry"]), "stop": dict(template["stop"]), "target": dict(template["target"]),
           "filters": {"session": ["london", "ny"] if market == "XAU/USD" else None, "news_blackout_min": 15},
           "params": dict(template["params"]), "source_id": source_id, "source_title": title[:160]}
    if idea in ("Seasonality", "Carry", "Volatility"):
        rec["notes"] = f"{idea}: approximated with the {gen} generator until a dedicated one exists"
    return rec


# -------------------------------------------------------------------------------------- round

def _handoff(a: str, b: str, item: str) -> None:
    emit("agent_handoff", {"from": a, "to": b, "item": item[:120]})


def _status(agent: str, status: str, item: str = "") -> None:
    emit("agent_status", {"agent": agent, "status": status, "item": item[:120]})


def run_round(queries: list[str] | None = None, kinds: list[str] | None = None, max_sources: int | None = None) -> dict:
    """One research round. Safe to run with no network: falls back to the offline corpus."""
    ensure()
    from nsq.db import conn
    c = conn()
    budget = Budget()
    queries = queries or setting("research.queries", DEFAULTS)
    kinds = kinds or setting("research.kinds", DEFAULTS)
    max_sources = max_sources or int(setting("research.max_sources_per_round", DEFAULTS))
    stats = {"searched": 0, "saved": 0, "rejected": 0, "summaries": 0, "terms": 0, "recipes": 0, "skipped": {},
             "mode": llm.mode(), "offline_used": False}
    _status("JARVIS", "working", f"round · {len(queries)} queries · {stats['mode']}")
    budget.emit()

    hits: list[dict] = []
    _status("SCOUT", "working", "searching")
    for q in queries:
        for k in kinds:
            if not budget.spend(COST["search"], "search"):
                break
            found, why = scout.search(k, q)
            stats["searched"] += 1
            if why:
                stats["skipped"][k] = why
                continue
            log("SEARCH", f'{k} "{q}" · {len(found)} results')
            for h in found:
                h["query"] = q
            hits += found
    known = {r["url"] for r in c.execute("SELECT url FROM sources").fetchall()}
    new_hits = [h for h in hits if h.get("url") and h["url"] not in known]
    if not new_hits:
        stats["offline_used"] = True
        for q in queries:
            for h in scout.offline(q):
                if h["url"] not in known and h["url"] not in {x["url"] for x in new_hits}:
                    h["query"] = q
                    new_hits.append(h)
        log("SEARCH", f"no new online sources · using built-in offline notes ({len(new_hits)})")
    _status("SCOUT", "idle")

    summariser = 0
    for h in new_hits[:max_sources]:
        if not budget.spend(COST["read"], "read"):
            break
        _handoff("SCOUT", "READER", h["title"])
        _status("READER", "working", h["title"])
        text = read(h)
        log("READ", f'opens "{h["title"][:70]}" · {len(text.split())} words')
        _handoff("READER", "WATCHER", h["title"])
        bad = lexicon.hype(h["title"] + " " + text)
        highlights = highlight(h["title"] + " " + text)
        if not bad and not highlights and not sum(lexicon.idea_scores(h["title"] + " " + text).values()):
            bad = "not about trading"
        synthetic = int(bool(h.get("synthetic")))
        if bad:
            c.execute("INSERT OR IGNORE INTO sources (kind, title, url, author, published, licence, excerpt, highlights_json, status,"
                      " reject_reason, synthetic, query, created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                      (h["kind"], h["title"], h["url"], h.get("author"), h.get("published"), h.get("licence"), text[:500],
                       jdump(highlights), "rejected", bad if bad == "not about trading" else f"hype: {bad}", synthetic, h.get("query"), now_ms()))
            log("REJECT", f'"{h["title"][:60]}" · ' + ("off topic" if bad == "not about trading" else f'promises fixed profit ("{bad}")'))
            stats["rejected"] += 1
            continue
        cur = c.execute("INSERT OR IGNORE INTO sources (kind, title, url, author, published, licence, excerpt, highlights_json, status,"
                        " synthetic, query, created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                        (h["kind"], h["title"], h["url"], h.get("author"), h.get("published"), h.get("licence"), text[:2000],
                         jdump(highlights), "saved", synthetic, h.get("query"), now_ms()))
        if not cur.rowcount:
            continue
        sid = cur.lastrowid
        stats["saved"] += 1

        # summarise (round-robin over the three summarisers)
        agent = f"SUMMARISER {summariser % 3 + 1}"
        summariser += 1
        _handoff("WATCHER", agent, h["title"])
        _status(agent, "working", h["title"])
        cost = COST["offline"] if not llm.available() else COST["llm_per_1k_tokens"] * max(0.5, len(text) / 4000)
        if not budget.spend(cost, "summarise"):
            break
        sm = llm.summarise(h["title"], text)
        c.execute("UPDATE sources SET idea_type=? WHERE id=?", (sm["idea_type"], sid))
        c.execute("INSERT INTO summaries (source_id, agent, summary, idea_type, confidence, model, created_at) VALUES (?,?,?,?,?,?,?)",
                  (sid, agent, sm["summary"], sm["idea_type"], sm["confidence"], sm["model"], now_ms()))
        emit("source_added", {"id": sid, "kind": h["kind"], "title": h["title"], "url": h["url"], "idea": sm["idea_type"],
                              "licence": h.get("licence"), "synthetic": bool(synthetic)})
        emit("summary_done", {"source_id": sid, "title": h["title"], "idea": sm["idea_type"], "summary": sm["summary"],
                              "agent": agent, "model": sm["model"], "highlights": highlights[:12]})
        log("SUMMARISE", f'"{h["title"][:60]}" → idea type {sm["idea_type"]}')
        log("SAVE", f"source saved · {sm['idea_type']} cluster")
        stats["summaries"] += 1
        _status(agent, "idle")

        # term checker
        _handoff(agent, "TERM-CHECKER", h["title"])
        cands = set(highlights) | set(lexicon.candidate_terms(text))
        try:
            from nsq.lab import kb
            kb.ensure()
            have = {r["slug"] for r in c.execute("SELECT slug FROM kb_concepts").fetchall()}
        except Exception:
            kb, have = None, set()
        for term in sorted(cands):
            slug = term.replace(" ", "_").replace("-", "_")
            if slug in have:
                continue
            r = c.execute("INSERT OR IGNORE INTO terms (term, status, first_source_id, created_at) VALUES (?,?,?,?)",
                          (term, "queued", sid, now_ms()))
            if r.rowcount:
                stats["terms"] += 1
                emit("term_found", {"term": term, "source_id": sid, "status": "queued"})
                log("TERM", f'new term "{term}" queued for checking')
                if kb:
                    kb.add_found(term, {"title": h["title"], "url": h["url"]})
            else:
                c.execute("UPDATE terms SET seen=seen+1 WHERE term=?", (term,))

        # recipe maker
        if setting("research.auto_recipe", DEFAULTS):
            _handoff("TERM-CHECKER", "RECIPE-MAKER", h["title"])
            _status("RECIPE-MAKER", "working", h["title"])
            rec = make_recipe(sid, h["title"], text, sm["idea_type"])
            from nsq.lab.runner import save_recipe
            save_recipe(rec, source_id=sid, origin="research")
            emit("recipe_created", {"id": rec["id"], "name": rec["name"], "market": rec["market"], "tf": rec["timeframe"],
                                    "idea_type": rec["idea_type"], "source_id": sid, "recipe": rec})
            log("SAVE", f"recipe {rec['name']} · {rec['market']} {rec['timeframe']} ready for the Lab")
            stats["recipes"] += 1
            _status("RECIPE-MAKER", "idle")
        _handoff("RECIPE-MAKER", "LAB", h["title"])

    p = budget.emit()
    log("BUDGET", f"think budget · {p['used']:.2f} of {p['of']:.0f} used")
    _status("JARVIS", "idle", f"round done · {stats['saved']} saved")
    audit_safe("research", "round_done", {k: v for k, v in stats.items() if k != "skipped"})
    return stats


def listing(table: str, limit: int = 100) -> list[dict]:
    if table not in ("sources", "summaries", "terms", "recipes"):
        raise ValueError(table)
    ensure()
    if table == "recipes":
        from nsq.lab.runner import ensure as e2
        e2()
    from nsq.db import conn
    return conn().execute(f"SELECT * FROM {table} ORDER BY id DESC LIMIT ?" if table != "recipes"
                          else "SELECT * FROM recipes ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
