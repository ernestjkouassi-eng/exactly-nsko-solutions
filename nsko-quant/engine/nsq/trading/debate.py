"""Multi-agent decision: analyst -> bull vs bear -> risk -> trader.

Uses a local Ollama model if one answers at localhost:11434, otherwise a deterministic rules-based debate.
The debate can VETO a trade. It can never override the risk gate: it only runs after the gate has passed,
and its only possible outputs are "take" or "veto".
"""
from __future__ import annotations

import json

from ..bus import publish
from ..settings import get


def _ollama_up(url: str) -> bool:
    try:
        import httpx
        return httpx.get(f"{url}/api/tags", timeout=0.6).status_code == 200
    except Exception:
        return False


def _rules(facts: dict) -> dict:
    bull, bear = [], []
    fa = facts.get("forecast_agree_pct", 50)
    (bull if fa >= 60 else bear if fa < 55 else bull).append(f"{fa:.0f}% of forecast paths agree")
    ev = facts.get("tm_ev_pts", 0)
    (bull if ev > 0 else bear).append(f"Time Machine edge {ev:+.4g} pts after costs")
    pt, ps = facts.get("p_target", 0), facts.get("p_stop", 0)
    (bull if pt > ps else bear).append(f"target first {pt}% vs stop first {ps}%")
    rr = facts.get("rr", 0)
    (bull if rr >= 1.5 else bear).append(f"reward:risk {rr:.2f}")
    if facts.get("trend_with_trade") is not None:
        (bull if facts["trend_with_trade"] else bear).append("trade is " + ("with" if facts["trend_with_trade"] else "against") + " the 50-bar trend")
    if facts.get("spread_frac", 0) > 0.15:
        bear.append(f"costs eat {facts['spread_frac'] * 100:.0f}% of the stop distance")
    verdict = "take" if len(bull) > len(bear) else "veto"
    return {"engine": "rules", "bull": bull, "bear": bear, "verdict": verdict,
            "trader": f"{'Take it' if verdict == 'take' else 'Pass'}: {len(bull)} points for, {len(bear)} against."}


def _llm(facts: dict, url: str, model: str) -> dict | None:
    try:
        import httpx
        prompt = ("You are a trading desk of four: analyst, bull, bear, trader. Facts (JSON): " + json.dumps(facts) +
                  '\nReply ONLY with JSON: {"bull":[...],"bear":[...],"verdict":"take"|"veto","trader":"one sentence"}. '
                  "You may only veto or take. You cannot change size, stop or target.")
        r = httpx.post(f"{url}/api/generate", json={"model": model, "prompt": prompt, "stream": False, "format": "json"},
                       timeout=30)
        out = json.loads(r.json().get("response", "{}"))
        if out.get("verdict") not in ("take", "veto"):
            return None
        return {"engine": f"ollama:{model}", "bull": out.get("bull", []), "bear": out.get("bear", []),
                "verdict": out["verdict"], "trader": out.get("trader", "")}
    except Exception:
        return None


def decide(facts: dict, plan_id: str | None = None, risk_passed: bool = True, use_llm: bool | None = None) -> dict:
    if not risk_passed:   # nothing to debate; the gate already said no and nobody can overrule it
        return {"engine": "none", "verdict": "veto", "bull": [], "bear": ["risk gate blocked"], "trader": "Blocked by risk."}
    for a in ("ANALYST", "BULL", "BEAR", "RISK", "TRADER"):
        publish("agent_status", {"agent": a, "state": "working", "plan_id": plan_id})
    url = get("debate.ollama_url")
    res = None
    if use_llm is not False and (use_llm or _ollama_up(url)):
        res = _llm(facts, url, get("debate.ollama_model"))
    if res is None:
        res = _rules(facts)
    res["risk"] = "risk gate passed (the debate cannot change it)"
    for a, b in (("ANALYST", "BULL"), ("ANALYST", "BEAR"), ("BULL", "RISK"), ("BEAR", "RISK"), ("RISK", "TRADER")):
        publish("agent_handoff", {"from": a, "to": b, "item": plan_id or "trade"})
    for a in ("ANALYST", "BULL", "BEAR", "RISK", "TRADER"):
        publish("agent_status", {"agent": a, "state": "idle", "plan_id": plan_id})
    return res
