"""Shared setup for the Stage 3 tests (imported by every stage3_*.py file).

- Puts engine/ on sys.path and points NSQ_DATA at a fresh temp folder before nsq.db is used.
- If the engine core (nsq.bus / nsq.db / nsq.audit / nsq.settings) is missing, installs small
  local shims that follow CONTRACT.md, so Stage 3 can be tested on its own.
- Makes every network call fail fast (tests must never depend on the internet).
"""
from __future__ import annotations

import os
import sqlite3
import sys
import tempfile
import threading
import types
from pathlib import Path

ENGINE = Path(__file__).resolve().parents[1]
if str(ENGINE) not in sys.path:
    sys.path.insert(0, str(ENGINE))
os.environ["NSQ_DATA"] = tempfile.mkdtemp(prefix="nsq-stage3-")


def _install_shims() -> None:
    try:
        import nsq.bus, nsq.db, nsq.audit, nsq.settings  # noqa: F401,E401
        return
    except ImportError:
        pass
    import json
    events: list = []
    bus = types.ModuleType("nsq.bus")
    subs: list = []
    bus.publish = lambda t, p: [f({"type": t, "ts": 0, "payload": p}) for f in list(subs)] and None
    bus.subscribe = lambda fn: (subs.append(fn), lambda: subs.remove(fn))[1]
    db = types.ModuleType("nsq.db")
    local = threading.local()
    db.data_dir = lambda: Path(os.environ["NSQ_DATA"])

    def conn():
        c = getattr(local, "c", None)
        if c is None:
            c = sqlite3.connect(Path(os.environ["NSQ_DATA"]) / "nsko.db", isolation_level=None, check_same_thread=False)
            c.row_factory = lambda cur, row: {d[0]: row[i] for i, d in enumerate(cur.description)}
            c.execute("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT, updated_at REAL)")
            c.execute("CREATE TABLE IF NOT EXISTS strategies (id TEXT PRIMARY KEY, name TEXT, market TEXT, timeframe TEXT, status TEXT,"
                      " intraday INTEGER, created_at REAL, updated_at REAL)")
            c.execute("CREATE TABLE IF NOT EXISTS strategy_versions (id INTEGER PRIMARY KEY AUTOINCREMENT, strategy_id TEXT, version INTEGER,"
                      " json_rules TEXT, source TEXT, metrics TEXT, note TEXT, created_at REAL)")
            local.c = c
        return c
    db.conn = conn
    audit = types.ModuleType("nsq.audit")
    audit.audit = lambda actor, action, detail=None: events.append((actor, action, detail))
    settings = types.ModuleType("nsq.settings")
    settings.get = lambda k, d=None: (lambda r: json.loads(r["value"]) if r else d)(conn().execute("SELECT value FROM settings WHERE key=?", (k,)).fetchone())
    settings.set = lambda k, v: conn().execute("INSERT OR REPLACE INTO settings VALUES (?,?,0)", (k, json.dumps(v)))
    for m in (bus, db, audit, settings):
        sys.modules[m.__name__] = m


_install_shims()

import nsq.db  # noqa: E402

if hasattr(nsq.db, "reset_for_tests"):
    nsq.db.reset_for_tests()


def offline() -> None:
    """Mark every host as blocked so no test touches the network."""
    from nsq.data import util

    def _no_net(*a, **k):
        raise util.Blocked("tests run offline")
    util._request = _no_net  # type: ignore[attr-defined]


offline()


class Recorder:
    def __init__(self):
        from nsq.bus import subscribe
        self.events: list[dict] = []
        self._unsub = subscribe(self.events.append)

    def types(self) -> list[str]:
        return [e["type"] for e in self.events]

    def of(self, t: str) -> list[dict]:
        return [e["payload"] for e in self.events if e["type"] == t]

    def close(self):
        if callable(self._unsub):
            self._unsub()


def candles(rows, start="2025-01-06 08:00", freq="15min"):
    """Hand-made candles from (open, high, low, close[, volume]) tuples."""
    import pandas as pd
    idx = pd.date_range(start, periods=len(rows), freq=freq, tz="UTC")
    df = pd.DataFrame([r if len(r) == 5 else (*r, 100.0) for r in rows], columns=["open", "high", "low", "close", "volume"], index=idx)
    df.index.name = "time"
    return df
