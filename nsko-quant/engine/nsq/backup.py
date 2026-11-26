"""Export / Restore my desk: one encrypted file with the account, settings, strategies and history.

NEVER includes broker keys or bot tokens (the vault is not exported; vault.* settings names are dropped).
Format: NSQ1 | salt | AES-256-GCM(json), key from Argon2id(passphrase). The user chooses the passphrase
(normally their account password).
"""
from __future__ import annotations

import json
import time

from . import __version__
from .audit import audit
from .crypto import open_with_passphrase, seal_with_passphrase
from .db import conn

AAD = b"nsq:backup"
TABLES = ["account", "settings", "strategies", "strategy_versions", "trade_plans", "orders", "fills", "positions",
          "journal", "risk_events", "alerts", "signals"]
OPTIONAL = ["recipes", "variants", "backtests", "sources", "summaries", "terms"]  # other modules' tables, if present
SECRET_SETTING_PREFIXES = ("vault.", "secret.", "telegram.bot_token")


def _tables() -> set[str]:
    return {r["name"] for r in conn().execute("SELECT name FROM sqlite_master WHERE type='table'")}


def export(passphrase: str) -> bytes:
    have = _tables()
    data = {"format": "nsko-quant-desk", "version": __version__, "exported_at": time.time(), "tables": {}}
    for t in TABLES + OPTIONAL:
        if t not in have:
            continue
        rows = conn().execute(f"SELECT * FROM {t}").fetchall()
        if t == "settings":
            rows = [r for r in rows if not r["key"].startswith(SECRET_SETTING_PREFIXES)]
        data["tables"][t] = rows
    blob = seal_with_passphrase(passphrase, json.dumps(data, default=str).encode(), AAD)
    audit("user", "desk.export", {"tables": {k: len(v) for k, v in data["tables"].items()}})
    return blob


def restore(blob: bytes, passphrase: str) -> dict:
    try:
        data = json.loads(open_with_passphrase(passphrase, blob, AAD))
    except Exception as e:
        raise ValueError("Wrong passphrase, or this is not an NSKO QUANT desk file.") from e
    if data.get("format") != "nsko-quant-desk":
        raise ValueError("Not an NSKO QUANT desk file.")
    c = conn()
    have = _tables()
    counts = {}
    c.execute("BEGIN IMMEDIATE")
    try:
        for t, rows in data["tables"].items():
            if t not in have or t == "audit_log":
                continue
            c.execute(f"DELETE FROM {t}")
            for r in rows:
                cols = list(r)
                c.execute(f"INSERT INTO {t} ({','.join(cols)}) VALUES ({','.join('?' * len(cols))})", [r[k] for k in cols])
            counts[t] = len(rows)
        c.execute("COMMIT")
    except Exception:
        c.execute("ROLLBACK")
        raise
    audit("user", "desk.restore", {"tables": counts, "from_version": data.get("version")})
    return {"ok": True, "restored": counts, "note": "Broker keys are not in backups. Reconnect your broker."}
