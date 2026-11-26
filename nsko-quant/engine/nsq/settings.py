"""Settings (CONTRACT.md): `get(key, default)` / `set(key, value)`, stored as JSON in the settings table.

DEFAULTS holds the section 9.4 defaults; `get` falls back to them when no value is stored.
"""
from __future__ import annotations

import json
import time
from typing import Any

from .db import conn

_MISSING = object()

DEFAULTS: dict[str, Any] = {
    # mode
    "mode": "paper",                    # paper | live (paper is the default)
    "trade_mode": "auto",               # auto | manual
    "manual_timeout_s": 60,             # manual approval timeout; default action is skip
    "broker": "paper",                  # the paper simulator is the default broker
    "demo": True,                       # demo event source when nothing is connected
    # risk (9.4)
    "risk.per_trade_pct": 1.0,
    "risk.daily_loss_pct": 3.0,
    "risk.weekly_loss_pct": 6.0,
    "risk.max_trades_per_day": 5,
    "risk.max_open_positions": 2,
    "risk.max_exposure_per_market_pct": 2.0,   # open risk on one market, % of equity
    "risk.max_spread_points": {},              # market -> max spread in price points
    "risk.default_max_spread_bps": 15.0,       # fallback: spread as basis points of price
    "risk.stale_data_s": 120,
    "risk.gate_enabled": True,                 # only honoured in paper; live always enforces
    # flow
    "news.blackout_min": 15,
    "news.calendar_file": "",                  # optional JSON file of events
    "news.use_data_calendar": True,            # also use the shipped calendar in nsq.data
    "news.events": [],                         # [{"time": iso, "impact": "high", "title", "currency"}]
    "forecast.paths": 1000,
    "forecast.horizon_bars": 16,
    "forecast.agree_pct": 55.0,
    "timemachine.replays": 10000,
    "timemachine.block": 8,
    "manage.scale_out_r": 1.0,
    "manage.scale_out_frac": 0.5,
    "manage.trail": False,
    "manage.trail_atr_mult": 1.5,
    "debate.ollama_url": "http://localhost:11434",
    "debate.ollama_model": "llama3.1",
    # live unlock (9.4)
    "live.paper_days_required": 21,
    "live.paper_trades_required": 30,
    "live.half_size_days": 14,
    "live.unlocked_at": None,
    # strategy updates (9.8)
    "updates.auto_margin_sharpe": 0.2,
    "updates.promote_live": "ask",             # auto | ask
    # notifications
    "notify.ntfy_url": "https://ntfy.sh",
    "notify.ntfy_topic": "",
    "notify.telegram_chat_id": "",
    # trading lock
    "trading.locked": False,
}


def get(key: str, default: Any = _MISSING) -> Any:
    row = conn().execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    if row is not None:
        return json.loads(row["value"])
    if default is not _MISSING:
        return default
    return DEFAULTS.get(key)


def set(key: str, value: Any) -> None:  # noqa: A001 - name fixed by the contract
    conn().execute(
        "INSERT INTO settings (key, value, updated_at) VALUES (?,?,?) "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at",
        (key, json.dumps(value), time.time()),
    )


def all_settings() -> dict[str, Any]:
    out = dict(DEFAULTS)
    for r in conn().execute("SELECT key, value FROM settings"):
        out[r["key"]] = json.loads(r["value"])
    return out
