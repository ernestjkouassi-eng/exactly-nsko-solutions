"""SQLite storage (CONTRACT.md).

`conn()` returns a sqlite3 connection in WAL mode with a dict row factory, to
`<data_dir>/nsko.db`. `data_dir()` is `$NSQ_DATA` or the OS app-data folder "NSKO QUANT".
Each module creates its own tables in an `ensure()` function; `ensure()` here creates the
core trading tables owned by the engine core.
"""
from __future__ import annotations

import os
import sqlite3
import sys
import threading
from pathlib import Path

_local = threading.local()
_ensured: set[str] = set()
_ensure_lock = threading.Lock()


def data_dir() -> Path:
    env = os.environ.get("NSQ_DATA")
    if env:
        p = Path(env)
    elif sys.platform == "win32":
        p = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming")) / "NSKO QUANT"
    elif sys.platform == "darwin":
        p = Path.home() / "Library" / "Application Support" / "NSKO QUANT"
    else:
        p = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share")) / "NSKO QUANT"
    p.mkdir(parents=True, exist_ok=True)
    return p


def db_path() -> Path:
    return data_dir() / "nsko.db"


def _dict_factory(cur: sqlite3.Cursor, row: tuple) -> dict:
    return {d[0]: row[i] for i, d in enumerate(cur.description)}


def conn() -> sqlite3.Connection:
    """One connection per thread per database path (autocommit mode, WAL)."""
    path = str(db_path())
    cache = getattr(_local, "conns", None)
    if cache is None:
        cache = _local.conns = {}
    c = cache.get(path)
    if c is None:
        c = sqlite3.connect(path, timeout=30, isolation_level=None, check_same_thread=False)
        c.row_factory = _dict_factory
        c.execute("PRAGMA journal_mode=WAL")
        c.execute("PRAGMA synchronous=NORMAL")
        c.execute("PRAGMA foreign_keys=ON")
        cache[path] = c
    if path not in _ensured:
        with _ensure_lock:
            if path not in _ensured:
                _ensured.add(path)
                ensure(c)
    return c


def reset_for_tests() -> None:
    """Drop cached connections (tests point NSQ_DATA at a fresh temp folder)."""
    cache = getattr(_local, "conns", None) or {}
    for c in cache.values():
        try:
            c.close()
        except Exception:
            pass
    _local.conns = {}
    _ensured.clear()


CORE_SCHEMA = """
CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL, updated_at REAL NOT NULL);
CREATE TABLE IF NOT EXISTS audit_log (
  id INTEGER PRIMARY KEY AUTOINCREMENT, ts REAL NOT NULL, actor TEXT NOT NULL, action TEXT NOT NULL,
  detail TEXT NOT NULL, prev_hash TEXT NOT NULL, hash TEXT NOT NULL);
CREATE TRIGGER IF NOT EXISTS audit_log_no_update BEFORE UPDATE ON audit_log
  BEGIN SELECT RAISE(ABORT, 'audit_log is append-only'); END;
CREATE TRIGGER IF NOT EXISTS audit_log_no_delete BEFORE DELETE ON audit_log
  BEGIN SELECT RAISE(ABORT, 'audit_log is append-only'); END;
CREATE TABLE IF NOT EXISTS strategies (
  id TEXT PRIMARY KEY, name TEXT NOT NULL, market TEXT NOT NULL, timeframe TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'lab', -- lab | paper | live | retired
  intraday INTEGER NOT NULL DEFAULT 1, live_version INTEGER, paper_version INTEGER,
  promote_mode TEXT NOT NULL DEFAULT 'ask', created_at REAL NOT NULL, updated_at REAL NOT NULL);
CREATE TABLE IF NOT EXISTS strategy_versions (
  id INTEGER PRIMARY KEY AUTOINCREMENT, strategy_id TEXT NOT NULL, version INTEGER NOT NULL,
  json_rules TEXT NOT NULL, source TEXT NOT NULL, metrics TEXT, note TEXT, created_at REAL NOT NULL,
  UNIQUE(strategy_id, version));
CREATE TABLE IF NOT EXISTS signals (
  id INTEGER PRIMARY KEY AUTOINCREMENT, strategy_id TEXT, market TEXT, time TEXT, side TEXT,
  entry REAL, stop REAL, target REAL, reason TEXT, created_at REAL NOT NULL);
CREATE TABLE IF NOT EXISTS trade_plans (
  id TEXT PRIMARY KEY, strategy_id TEXT, market TEXT, side TEXT, entry REAL, stop REAL, target REAL,
  size REAL, state TEXT NOT NULL, mode TEXT, detail TEXT, created_at REAL NOT NULL, updated_at REAL NOT NULL);
CREATE TABLE IF NOT EXISTS orders (
  id TEXT PRIMARY KEY, client_order_id TEXT UNIQUE NOT NULL, broker TEXT NOT NULL, plan_id TEXT,
  market TEXT NOT NULL, side TEXT NOT NULL, kind TEXT NOT NULL, qty REAL NOT NULL, price REAL,
  status TEXT NOT NULL, parent_id TEXT, created_at REAL NOT NULL, updated_at REAL NOT NULL);
CREATE TABLE IF NOT EXISTS fills (
  id INTEGER PRIMARY KEY AUTOINCREMENT, order_id TEXT NOT NULL, broker TEXT NOT NULL, market TEXT NOT NULL,
  side TEXT NOT NULL, qty REAL NOT NULL, price REAL NOT NULL, commission REAL NOT NULL DEFAULT 0, ts REAL NOT NULL);
CREATE TABLE IF NOT EXISTS positions (
  id TEXT PRIMARY KEY, broker TEXT NOT NULL, plan_id TEXT, strategy_id TEXT, market TEXT NOT NULL,
  side TEXT NOT NULL, qty REAL NOT NULL, entry REAL NOT NULL, stop REAL, target REAL, initial_qty REAL,
  initial_stop REAL, realised REAL NOT NULL DEFAULT 0, status TEXT NOT NULL, mode TEXT NOT NULL DEFAULT 'paper',
  opened_at REAL NOT NULL, closed_at REAL, exit_price REAL, exit_reason TEXT);
CREATE TABLE IF NOT EXISTS risk_events (
  id INTEGER PRIMARY KEY AUTOINCREMENT, ts REAL NOT NULL, plan_id TEXT, market TEXT, rule TEXT NOT NULL,
  passed INTEGER NOT NULL, reason TEXT NOT NULL, detail TEXT);
CREATE TABLE IF NOT EXISTS alerts (
  id INTEGER PRIMARY KEY AUTOINCREMENT, ts REAL NOT NULL, level TEXT NOT NULL, kind TEXT NOT NULL,
  title TEXT NOT NULL, body TEXT, channels TEXT, delivered TEXT);
CREATE TABLE IF NOT EXISTS journal (
  id INTEGER PRIMARY KEY AUTOINCREMENT, ts REAL NOT NULL, plan_id TEXT, position_id TEXT, market TEXT,
  side TEXT, pnl REAL, r_multiple REAL, mode TEXT, detail TEXT);
CREATE TABLE IF NOT EXISTS account (
  id INTEGER PRIMARY KEY CHECK (id = 1), name TEXT, email TEXT NOT NULL, pw_hash TEXT NOT NULL,
  pin_hash TEXT, totp_enc TEXT, recovery_hash TEXT NOT NULL, kdf_salt TEXT NOT NULL,
  dek_by_pw TEXT NOT NULL, dek_by_recovery TEXT NOT NULL, created_at REAL NOT NULL);
"""


def ensure(c: sqlite3.Connection | None = None) -> None:
    c = c or conn()
    c.executescript(CORE_SCHEMA)
