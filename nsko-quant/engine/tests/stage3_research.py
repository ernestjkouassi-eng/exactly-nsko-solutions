"""JARVIS research pipeline offline: events, storage, hype rejection, recipes, budget."""
import stage3_helpers as h
from nsq.lab import signals
from nsq.research import lexicon, llm, pipeline


def test_offline_round_end_to_end():
    llm._state.update(checked=1e18, up=False)          # no Ollama in tests
    rec = h.Recorder()
    s = pipeline.run_round(["volume profile liquidity sweep", "opening range breakout gold", "always wins"], kinds=["GitHub", "arXiv"])
    rec.close()
    assert s["offline_used"] and s["saved"] >= 3 and s["rejected"] >= 1 and s["mode"] == "offline"
    t = set(rec.types())
    for need in ("ticker_log", "agent_status", "agent_handoff", "source_added", "summary_done", "term_found",
                 "recipe_created", "budget_update"):
        assert need in t, need
    verbs = {p["verb"] for p in rec.of("ticker_log")}
    assert {"SEARCH", "READ", "SUMMARISE", "SAVE", "REJECT", "TERM", "BUDGET"} <= verbs
    for p in rec.of("summary_done"):
        assert p["idea"] in lexicon.IDEA_TYPES and p["summary"]
    for p in rec.of("recipe_created"):
        r = p["recipe"]
        assert {"id", "name", "market", "timeframe", "idea_type", "entry", "stop", "target", "filters", "params"} <= set(r)
        signals.generator_for(r)
    from nsq.db import conn
    c = conn()
    for tbl in ("sources", "summaries", "terms", "recipes"):
        assert c.execute(f"SELECT COUNT(*) n FROM {tbl}").fetchone()["n"] > 0, tbl
    rej = c.execute("SELECT * FROM sources WHERE status='rejected'").fetchall()
    assert rej and "hype" in rej[0]["reject_reason"]
    of = c.execute("SELECT idea_type FROM sources WHERE title LIKE 'Reading the volume profile%'").fetchone()
    assert of["idea_type"] == "Orderflow"


def test_second_round_does_not_duplicate_sources():
    llm._state.update(checked=1e18, up=False)
    pipeline.run_round(["vwap"], kinds=[])
    from nsq.db import conn
    n1 = conn().execute("SELECT COUNT(*) n FROM sources").fetchone()["n"]
    pipeline.run_round(["vwap"], kinds=[])
    n2 = conn().execute("SELECT COUNT(*) n FROM sources").fetchone()["n"]
    assert n2 - n1 <= 3 and n2 >= n1


def test_budget_pauses_round():
    from nsq.settings import set as sset
    llm._state.update(checked=1e18, up=False)
    sset("research.daily_budget", 0.12)
    rec = h.Recorder()
    s = pipeline.run_round(["momentum"], kinds=[])
    rec.close()
    assert s["summaries"] <= 1
    assert any(p["verb"] == "PAUSE" for p in rec.of("ticker_log"))
    b = rec.of("budget_update")[-1]
    assert b["of"] == 0.12 and b["used"] <= 0.12


def test_classifier_and_hype():
    assert lexicon.classify("fade the stretch back to vwap, mean reversion")[0] == "Mean reversion"
    assert lexicon.classify("funding rate carry in contango")[0] == "Carry"
    assert lexicon.hype("This system ALWAYS WINS") is not None
    assert lexicon.hype("a modest edge after costs") is None
    assert "fair value gap" in lexicon.find_terms("We mark the Fair Value Gap first.")


def test_offline_summary_is_deterministic():
    t = ("Price that stretches two standard deviations from VWAP often reverts. Mean reversion fades the stretch. "
         "The weather was nice today and nothing else happened at all here. It fails on trend days with momentum.")
    a, b = llm.summarise("x", t), llm.summarise("x", t)
    assert a == b and a["model"] == "offline" and a["idea_type"] == "Mean reversion"
