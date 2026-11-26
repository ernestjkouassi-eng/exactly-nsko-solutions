"""JARVIS chat for the desk's side panel (POST /jarvis/chat).

Uses the LOCAL model through Ollama (http://localhost:11434) when it is running. Nothing leaves the machine.
When Ollama is not installed or not running, JARVIS says so plainly and answers only with facts the engine
knows for certain (mode, kill switch, account, open positions, limits). It never makes up an answer.
"""
from __future__ import annotations

import json

NOT_INSTALLED = ("The local AI model is not installed or not running on this computer, so I cannot answer "
                 "open questions yet. To turn me on: install Ollama (ollama.com), then run `ollama pull llama3.1` "
                 "and keep it running. Everything stays on this computer.")


def facts() -> dict:
    """Plain facts from the engine. Each one is read, never guessed; a failed read is left out."""
    out: dict = {}
    try:
        from .settings import get
        out.update(mode=get("mode"), trade_mode=get("trade_mode"), paused=bool(get("trading.paused", False)),
                   limits={"per_trade_pct": get("risk.per_trade_pct"), "daily_loss_pct": get("risk.daily_loss_pct"),
                           "weekly_loss_pct": get("risk.weekly_loss_pct"), "max_trades_per_day": get("risk.max_trades_per_day"),
                           "max_open_positions": get("risk.max_open_positions"), "news_blackout_min": get("news.blackout_min")})
        from .trading.killswitch import is_locked
        out["locked"], out["lock_reason"] = is_locked()
    except Exception:
        pass
    try:
        from .brokers import active
        b = active()
        a = b.account()
        out.update(broker=b.name, equity=round(a.equity, 2), currency=a.currency,
                   positions=[{"market": p.market, "side": p.side, "qty": p.qty, "entry": p.entry, "stop": p.stop,
                               "target": p.target} for p in b.positions()])
    except Exception:
        pass
    return out


def facts_text(f: dict) -> str:
    bits = []
    if "mode" in f:
        bits.append(f"Mode: {str(f['mode']).upper()} · {f.get('trade_mode', 'auto')}"
                    + (" · new trades PAUSED" if f.get("paused") else ""))
    if f.get("locked"):
        bits.append(f"Trading is locked: {f.get('lock_reason')}")
    if "equity" in f:
        bits.append(f"Account ({f.get('broker')}): {f['equity']:,.2f} {f.get('currency', '')}")
        pos = f.get("positions") or []
        bits.append(f"Open positions: {len(pos)}" + ("".join(f"\n  · {p['side'].upper()} {p['market']} {p['qty']} @ {p['entry']}"
                                                              for p in pos) if pos else ""))
    if "limits" in f:
        L = f["limits"]
        bits.append(f"Limits: {L['per_trade_pct']}% per trade, {L['daily_loss_pct']}% daily, {L['weekly_loss_pct']}% weekly, "
                    f"{L['max_trades_per_day']} trades a day, {L['max_open_positions']} open, news blackout ±{L['news_blackout_min']} min")
    return "\n".join(bits)


def chat(message: str, history: list[dict] | None = None) -> dict:
    from .research import llm
    f = facts()
    if not llm.available(recheck_s=15):
        return {"reply": NOT_INSTALLED + ("\n\nWhat I can tell you for certain:\n" + facts_text(f) if f else ""),
                "model": None, "local_model": False, "facts": f}
    convo = "".join(f"{'User' if h.get('me') else 'JARVIS'}: {str(h.get('t', ''))[:600]}\n" for h in (history or [])[-6:])
    prompt = ("You are JARVIS, the assistant inside NSKO QUANT, a trading desk that runs on the user's own computer. "
              "Answer briefly, in plain English. Use ONLY the facts below for anything about the user's account, "
              "positions or settings; if the facts do not answer it, say you do not know. Never promise profits. "
              "You cannot place, change or cancel trades; tell the user to use the desk for that.\n\n"
              f"FACTS (from the engine, JSON): {json.dumps(f, default=str)}\n\n{convo}User: {message[:2000]}\nJARVIS:")
    out = llm.generate(prompt, as_json=False, timeout=90)
    if not out:
        return {"reply": "The local model did not answer in time. Try again in a moment.\n\n" + facts_text(f),
                "model": llm.mode(), "local_model": True, "facts": f}
    return {"reply": out.strip(), "model": llm.mode(), "local_model": True, "facts": f}
