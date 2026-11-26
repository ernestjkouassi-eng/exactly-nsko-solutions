"""Structured JSON logger with secret redaction.

Every log line passes through `redact()`: values of key-like fields and anything that looks like
a token/API key are replaced with ****REDACTED****. Never log a secret on purpose anyway.
"""
from __future__ import annotations

import json
import logging
import re
import sys
import time
from typing import Any

REDACTED = "****REDACTED****"
_SECRET_KEYS = re.compile(r"(^|[_\-.])(api_?key|key|key_?id|secret|api_?secret|token|bot_?token|password|passwd|pwd|pin|totp|totp_?secret|bearer|signature|cookie|recovery(_?code)?|private_?key|passphrase|cst|x-security-token)($|[_\-.])", re.I)
_PATTERNS = [
    re.compile(r"(?i)\b(bearer|token|apikey|api_key|api-key|secret|password|passphrase|key|pin)\b(\s*[=:]\s*|(?<=bearer)\s+|(?<=Bearer)\s+)([^\s,;\"'&]+)"),
    re.compile(r"\b\d{6,12}:[A-Za-z0-9_-]{30,}\b"),          # Telegram bot tokens
    re.compile(r"\b(sk|pk|rk)_(live|test)_[A-Za-z0-9]{10,}\b"),
    re.compile(r"\b(?=[A-Za-z0-9+/]*[A-Z])(?=[A-Za-z0-9+/]*[a-z])[A-Za-z0-9+/]{40,}={0,2}"),  # long mixed-case base64 (API secrets)
    re.compile(r"\bPK[A-Z0-9]{14,}\b|\bAK[A-Z0-9]{14,}\b"),   # Alpaca-style key ids
]


def redact(text: str) -> str:
    if not isinstance(text, str):
        text = str(text)
    out = _PATTERNS[0].sub(lambda m: f"{m.group(1)}{m.group(2)}{REDACTED}", text)
    for p in _PATTERNS[1:]:
        out = p.sub(REDACTED, out)
    return out


def redact_obj(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {k: (REDACTED if (isinstance(k, str) and _SECRET_KEYS.search(k) and v not in (None, "", False))
                    and not isinstance(v, (bool, int, float)) else redact_obj(v)) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [redact_obj(v) for v in obj]
    if isinstance(obj, str):
        return redact(obj)
    return obj


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        d = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(record.created)) + f".{int(record.msecs):03d}Z",
             "level": record.levelname, "logger": record.name, "msg": redact(record.getMessage())}
        extra = getattr(record, "fields", None)
        if extra:
            d["fields"] = redact_obj(extra)
        if record.exc_info:
            d["exc"] = redact(self.formatException(record.exc_info))
        return json.dumps(d, default=str)


_configured = False


def setup(level: str = "INFO", file: str | None = None) -> None:
    global _configured
    if _configured:
        return
    _configured = True
    root = logging.getLogger("nsq")
    root.setLevel(level)
    h = logging.StreamHandler(sys.stderr)
    h.setFormatter(JsonFormatter())
    root.addHandler(h)
    if file:
        from logging.handlers import RotatingFileHandler
        fh = RotatingFileHandler(file, maxBytes=5_000_000, backupCount=5)
        fh.setFormatter(JsonFormatter())
        root.addHandler(fh)


def get(name: str) -> logging.Logger:
    return logging.getLogger(f"nsq.{name}")


def info(logger: logging.Logger, msg: str, **fields: Any) -> None:
    logger.info(msg, extra={"fields": fields} if fields else None)
