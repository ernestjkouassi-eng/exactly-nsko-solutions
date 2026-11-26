"""Trading vocabulary used by READER/WATCHER (highlights), the SUMMARISERS (idea type) and the
TERM-CHECKER (new terms for the Knowledge Base)."""
from __future__ import annotations

import re

IDEA_TYPES = ["Trend following", "Mean reversion", "Breakout", "Volatility", "Orderflow", "Seasonality", "Carry"]

IDEA_KEYWORDS: dict[str, list[str]] = {
    "Trend following": ["trend following", "momentum", "moving average", "time-series momentum", "ema cross", "trend",
                        "donchian", "turtle", "higher highs", "ride the trend"],
    "Mean reversion": ["mean reversion", "revert", "reversion", "vwap", "overbought", "oversold", "rsi", "bollinger",
                       "pairs trading", "cointegration", "z-score", "fade"],
    "Breakout": ["breakout", "opening range", "range break", "orb", "consolidation", "squeeze", "break of structure",
                 "new high", "channel break"],
    "Volatility": ["volatility", "atr", "vix", "implied vol", "garch", "straddle", "variance", "volatility breakout",
                   "regime"],
    "Orderflow": ["order flow", "orderflow", "volume profile", "footprint", "delta", "point of control", "value area",
                  "liquidity sweep", "absorption", "market profile", "fair value gap", "order block", "imbalance",
                  "aggressive buyers", "tape"],
    "Seasonality": ["seasonality", "seasonal", "day of week", "month of year", "turn of the month", "calendar effect",
                    "holiday effect", "time of day"],
    "Carry": ["carry", "roll yield", "contango", "backwardation", "interest rate differential", "funding rate", "basis"],
}

# terms the Knowledge Base knows or wants to know about (TERM-CHECKER queues new ones)
TERMS = sorted({
    "fair value gap", "order block", "liquidity sweep", "break of structure", "change of character", "displacement",
    "point of control", "value area", "value area high", "value area low", "low volume node", "high volume node",
    "vwap", "vwap band", "opening range", "asia range", "equal highs", "equal lows", "inside bar", "swing high",
    "swing low", "market structure", "premium and discount", "optimal trade entry", "mitigation block", "breaker block",
    "liquidity void", "imbalance", "absorption", "delta divergence", "cumulative delta", "footprint", "initial balance",
    "poor high", "poor low", "single prints", "excess", "kill zone", "judas swing", "power of three", "turtle soup",
    "time-series momentum", "cross-sectional momentum", "roll yield", "contango", "backwardation", "funding rate",
    "atr stop", "chandelier exit", "kelly criterion", "walk-forward", "overfitting", "sharpe ratio", "drawdown",
})

HYPE = [r"always wins?", r"guarantee[ds]?", r"100\s?% win", r"never lose", r"no[- ]loss", r"risk[- ]free profit",
        r"fixed (daily )?profit", r"get rich", r"secret indicator", r"\d+\s?% (a|per) (day|week) guaranteed"]
_HYPE_RE = re.compile("|".join(HYPE), re.I)


def hype(text: str) -> str | None:
    m = _HYPE_RE.search(text or "")
    return m.group(0) if m else None


def find_terms(text: str) -> list[str]:
    t = (text or "").lower()
    return [term for term in TERMS if re.search(r"\b" + re.escape(term) + r"\b", t)]


def idea_scores(text: str) -> dict[str, int]:
    t = (text or "").lower()
    return {k: sum(len(re.findall(r"\b" + re.escape(w) + r"\b", t)) for w in words) for k, words in IDEA_KEYWORDS.items()}


def classify(text: str) -> tuple[str, float]:
    s = idea_scores(text)
    total = sum(s.values())
    if not total:
        return "Trend following", 0.0
    best = max(IDEA_TYPES, key=lambda k: (s[k], -IDEA_TYPES.index(k)))
    return best, round(s[best] / total, 2)


CANDIDATE_TERM_RE = re.compile(r"\b(?:[a-z]+[- ]){0,2}(?:gap|block|sweep|node|band|range|structure|delta|imbalance|"
                               r"liquidity|profile|swing|void|trap|squeeze)\b", re.I)


def candidate_terms(text: str) -> list[str]:
    """Unknown phrases that look like trading jargon (e.g. 'breaker block', 'liquidity void')."""
    found = {m.group(0).lower().strip() for m in CANDIDATE_TERM_RE.finditer(text or "")}
    stop = {"the", "a", "an", "this", "that", "of", "in", "on", "and", "to", "is", "for", "with"}
    out = []
    for f in found:
        words = [w for w in re.split(r"[- ]", f) if w and w not in stop]
        if 2 <= len(words) <= 3:
            out.append(" ".join(words))
    return sorted(set(out))
