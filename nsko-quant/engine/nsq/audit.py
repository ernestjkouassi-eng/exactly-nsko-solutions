"""Append-only, hash-chained audit log (CONTRACT.md).

Each row stores `prev_hash` and `hash = sha256(prev_hash | ts | actor | action | detail_json)`.
SQLite triggers refuse UPDATE and DELETE. `verify_chain()` recomputes every hash, so any edit
made behind the engine's back (for example with the triggers dropped) is detected.
"""
from __future__ import annotations

import hashlib
import json
import threading
import time

from .db import conn
from .log import redact_obj

GENESIS = "0" * 64
_lock = threading.Lock()


def _hash(prev: str, ts: float, actor: str, action: str, detail: str) -> str:
    h = hashlib.sha256()
    h.update("|".join([prev, repr(float(ts)), actor, action, detail]).encode())
    return h.hexdigest()


def audit(actor: str, action: str, detail: dict | None = None) -> str:
    """Append one entry. Secrets in `detail` are redacted before they are stored."""
    detail_json = json.dumps(redact_obj(detail or {}), sort_keys=True, default=str)
    with _lock:
        c = conn()
        c.execute("BEGIN IMMEDIATE")
        try:
            row = c.execute("SELECT hash FROM audit_log ORDER BY id DESC LIMIT 1").fetchone()
            prev = row["hash"] if row else GENESIS
            ts = time.time()
            h = _hash(prev, ts, actor, action, detail_json)
            c.execute(
                "INSERT INTO audit_log (ts, actor, action, detail, prev_hash, hash) VALUES (?,?,?,?,?,?)",
                (ts, actor, action, detail_json, prev, h),
            )
            c.execute("COMMIT")
        except Exception:
            c.execute("ROLLBACK")
            raise
    return h


def verify_chain() -> dict:
    """Recompute the whole chain. Returns {"ok": bool, "count": n, "bad_id": id|None, "reason"}."""
    prev = GENESIS
    n = 0
    for row in conn().execute("SELECT * FROM audit_log ORDER BY id ASC"):
        n += 1
        if row["prev_hash"] != prev:
            return {"ok": False, "count": n, "bad_id": row["id"], "reason": "prev_hash does not link"}
        if _hash(prev, row["ts"], row["actor"], row["action"], row["detail"]) != row["hash"]:
            return {"ok": False, "count": n, "bad_id": row["id"], "reason": "hash mismatch (row edited)"}
        prev = row["hash"]
    return {"ok": True, "count": n, "bad_id": None, "reason": "chain intact"}


def tail(n: int = 50) -> list[dict]:
    rows = conn().execute("SELECT * FROM audit_log ORDER BY id DESC LIMIT ?", (n,)).fetchall()
    for r in rows:
        r["detail"] = json.loads(r["detail"])
    return rows
