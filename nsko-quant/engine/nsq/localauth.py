"""Local shared secret for the desktop shell (tray menu).

The Tauri shell's tray runs in Rust with no user session, but it must be able to pause trading and quit the
engine even when the window is closed and nobody is logged in. At start the engine writes a random token to
`<data_dir>/shell.token` (owner-only permissions). The shell reads that file and sends it as `X-NSQ-Shell`.
Only a process running as the same OS user can read the file, so a web page cannot get it.

The kill switch never needs this token: `/kill` always works without a login.
"""
from __future__ import annotations

import hmac
import os
import secrets
from pathlib import Path

from .db import data_dir

FILE = "shell.token"
HEADER = "x-nsq-shell"
_token: str | None = None


def path() -> Path:
    return data_dir() / FILE


def write() -> str:
    """Create a fresh token for this engine run and write it with owner-only permissions."""
    global _token
    _token = secrets.token_urlsafe(32)
    p = path()
    tmp = p.with_suffix(".tmp")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        f.write(_token)
    os.replace(tmp, p)
    try:
        os.chmod(p, 0o600)
    except OSError:   # Windows: the file sits in the user's own %APPDATA%, which only that user can read
        pass
    return _token


def current() -> str:
    """The token for this run (written on first use if the engine was not started through the lifespan)."""
    return _token or write()


def check(value: str | None) -> bool:
    return bool(value) and hmac.compare_digest(value.encode(), current().encode())


def _reset_for_tests() -> None:
    global _token
    _token = None
