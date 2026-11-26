"""Local model via Ollama (http://localhost:11434) when it is running, else a deterministic
offline fallback. Nothing leaves the machine: Ollama is local, the fallback is plain Python.

Ollama endpoints used (documented in the Ollama API reference): GET /api/tags (is it up, which
models), POST /api/generate {"model", "prompt", "stream": false, "format": "json"}.
"""
from __future__ import annotations

import json
import re
import time
import urllib.request

from nsq.data.util import setting

from . import lexicon

DEFAULTS = {"research.ollama_url": None, "research.ollama_model": None}
_state = {"checked": 0.0, "up": False, "models": []}


def _url() -> str:
    return setting("research.ollama_url", DEFAULTS) or setting("debate.ollama_url", {"debate.ollama_url": "http://localhost:11434"})


def _model() -> str:
    return setting("research.ollama_model", DEFAULTS) or setting("debate.ollama_model", {"debate.ollama_model": "llama3.1"})


def available(recheck_s: float = 120) -> bool:
    if time.time() - _state["checked"] < recheck_s:
        return _state["up"]
    _state["checked"] = time.time()
    try:  # localhost: no proxy, short timeout
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open(_url().rstrip("/") + "/api/tags", timeout=2) as r:
            data = json.loads(r.read())
        _state["models"] = [m.get("name") for m in data.get("models", [])]
        _state["up"] = True
    except Exception:
        _state["up"] = False
    return _state["up"]


def generate(prompt: str, as_json: bool = True, timeout: float = 120) -> str | None:
    if not available():
        return None
    body = {"model": _model(), "prompt": prompt, "stream": False}
    if as_json:
        body["format"] = "json"
    req = urllib.request.Request(_url().rstrip("/") + "/api/generate", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"}, method="POST")
    try:
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open(req, timeout=timeout) as r:
            return json.loads(r.read()).get("response")
    except Exception:
        return None


def mode() -> str:
    return f"ollama:{_model()}" if available() else "offline"


# ------------------------------------------------------------------------- offline summariser

def _sentences(text: str) -> list[str]:
    s = re.split(r"(?<=[.!?])\s+", re.sub(r"\s+", " ", text or "").strip())
    return [x for x in s if 30 <= len(x) <= 400]


def offline_summary(text: str, n: int = 3) -> str:
    """Extractive: the n sentences with the most trading vocabulary, kept in original order."""
    sents = _sentences(text)
    if not sents:
        return (text or "")[:280]
    words = [w for ws in lexicon.IDEA_KEYWORDS.values() for w in ws] + lexicon.TERMS
    scored = []
    for i, s in enumerate(sents):
        low = s.lower()
        score = sum(low.count(w) for w in words) + (0.5 if i == 0 else 0)
        scored.append((score, i, s))
    top = sorted(sorted(scored, key=lambda x: (-x[0], x[1]))[:n], key=lambda x: x[1])
    return " ".join(s for _, _, s in top)


def summarise(title: str, text: str) -> dict:
    """{summary, idea_type, confidence, model}. Uses Ollama if up; validates its answer."""
    prompt = ("You are a trading research assistant. Read the text and answer in JSON with keys "
              "'summary' (3 plain-English sentences, no hype) and 'idea_type' (exactly one of: "
              + ", ".join(lexicon.IDEA_TYPES) + ").\n\nTITLE: " + title + "\n\nTEXT:\n" + (text or "")[:6000])
    raw = generate(prompt)
    if raw:
        try:
            d = json.loads(raw)
            it = d.get("idea_type")
            if it in lexicon.IDEA_TYPES and d.get("summary"):
                return {"summary": str(d["summary"])[:1200], "idea_type": it, "confidence": 0.8, "model": mode()}
        except Exception:
            pass
    it, conf = lexicon.classify(title + " " + (text or ""))
    return {"summary": offline_summary(text), "idea_type": it, "confidence": conf, "model": "offline"}
