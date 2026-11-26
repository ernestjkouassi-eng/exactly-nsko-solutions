"""Push notifications: ntfy (ntfy.sh or self-hosted) and Telegram (free Bot API).

Sent for every trade, error, kill switch and the daily summary. Desktop notifications are the app's job.
Telegram bot token lives in the vault ("telegram.bot_token"); the paired chat id is in settings.
The Telegram `/kill` command is honoured ONLY from the paired chat id.
Sending happens on a background thread; failures are logged (redacted) and never break trading.
"""
from __future__ import annotations

import threading
import time

from .bus import publish
from .db import conn
from .log import get as get_log
from .settings import get

_log = get_log("notify")
TG_API = "https://api.telegram.org"
PRIORITY = {"info": "default", "trade": "high", "error": "high", "critical": "urgent"}
_sent: list[dict] = []    # tests read this
_http = None


def _client():
    global _http
    if _http is None:
        import httpx
        _http = httpx.Client(timeout=10)
    return _http


def _ntfy(title: str, body: str, level: str) -> str:
    topic = get("notify.ntfy_topic")
    if not topic:
        return "skipped"
    url = f"{str(get('notify.ntfy_url')).rstrip('/')}/{topic}"
    r = _client().post(url, content=body.encode(), headers={
        "Title": title, "Priority": PRIORITY.get(level, "high"), "Tags": "chart_with_upwards_trend"})
    return "ok" if r.status_code < 300 else f"http {r.status_code}"


def _telegram(title: str, body: str) -> str:
    from . import vault
    chat = get("notify.telegram_chat_id")
    token = vault.get("telegram.bot_token")
    if not chat or not token:
        return "skipped"
    r = _client().post(f"{TG_API}/bot{token}/sendMessage", json={"chat_id": chat, "text": f"{title}\n{body}"})
    return "ok" if r.status_code < 300 else f"http {r.status_code}"


def notify(kind: str, title: str, body: str, level: str = "trade", sync: bool = False) -> int:
    """kind: trade | error | kill | summary | info. Records the alert, publishes `alert`, pushes out."""
    c = conn()
    cur = c.execute("INSERT INTO alerts (ts, level, kind, title, body, channels, delivered) VALUES (?,?,?,?,?,?,?)",
                    (time.time(), level, kind, title, body, "ntfy,telegram", "pending"))
    aid = cur.lastrowid
    publish("alert", {"id": aid, "kind": kind, "level": level, "title": title, "body": body})
    _sent.append({"kind": kind, "title": title, "body": body, "level": level})

    def _go() -> None:
        res = {}
        for name, fn in (("ntfy", lambda: _ntfy(title, body, level)), ("telegram", lambda: _telegram(title, body))):
            if not get(f"notify.{name}_enabled", True):
                res[name] = "off in settings"
                continue
            try:
                res[name] = fn()
            except Exception as e:  # network down etc.
                res[name] = f"error {type(e).__name__}"
                _log.warning(f"notify {name} failed: {e}")
        try:
            conn().execute("UPDATE alerts SET delivered=? WHERE id=?", (str(res), aid))
        except Exception:
            pass

    if sync or get("notify.ntfy_topic") == "" and not get("notify.telegram_chat_id"):
        _go()
    else:
        threading.Thread(target=_go, daemon=True).start()
    return aid


# ---------------------------------------------------------------------- Telegram commands
_offset = 0


def handle_telegram_update(update: dict) -> str | None:
    """Process one Bot API update. Only the paired chat may run commands."""
    msg = update.get("message") or {}
    chat_id = str((msg.get("chat") or {}).get("id", ""))
    text = (msg.get("text") or "").strip().lower()
    paired = str(get("notify.telegram_chat_id") or "")
    if not text.startswith("/"):
        return None
    if not paired or chat_id != paired:
        from .audit import audit
        audit("telegram", "command_refused", {"chat_id": chat_id, "cmd": text[:20]})
        return "refused"
    if text.startswith("/kill"):
        from .trading.killswitch import kill
        kill(source="telegram", reason="Telegram /kill")
        return "killed"
    if text.startswith("/status"):
        from .brokers import active
        a = active().account()
        notify("info", "Status", f"Equity £{a.equity:,.2f} · open positions {len(active().positions())}", level="info")
        return "status"
    return None


def poll_telegram() -> None:
    """Long-poll getUpdates once (scheduled job). No webhook needed, nothing exposed to the internet."""
    global _offset
    from . import vault
    token = vault.get("telegram.bot_token")
    if not token:
        return
    try:
        r = _client().get(f"{TG_API}/bot{token}/getUpdates", params={"offset": _offset, "timeout": 0})
        for u in r.json().get("result", []):
            _offset = max(_offset, u["update_id"] + 1)
            handle_telegram_update(u)
    except Exception as e:
        _log.warning(f"telegram poll failed: {type(e).__name__}")


def daily_summary() -> int:
    import datetime as dt
    day0 = dt.datetime.now(dt.timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0).timestamp()
    r = conn().execute("SELECT COUNT(*) n, COALESCE(SUM(pnl),0) p, COALESCE(SUM(CASE WHEN pnl>0 THEN 1 ELSE 0 END),0) w "
                       "FROM journal WHERE ts>=?", (day0,)).fetchone()
    mode = get("mode")
    return notify("summary", f"Daily summary ({mode.upper()})",
                  f"{r['n']} trades · {r['w']} winners · P&L £{r['p']:,.2f}", level="info")
