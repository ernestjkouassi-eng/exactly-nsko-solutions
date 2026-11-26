"""Shared helpers for the Stage 3 packages (data, research, lab, godseye).

- `http_get` / `http_post_json`: polite HTTP with a per-host rate limit, an optional robots.txt
  check, and a "probe each host once" rule: a host that fails at the network level is remembered
  as blocked for this process, and callers fall back to cache or synthetic data.
- `ensure_table`: CREATE TABLE IF NOT EXISTS, then add any missing columns (never drops anything),
  so two modules that touch the same table cannot break each other.
- `secret(name)`: bring-your-own keys. Looked up in the engine keychain if one exists, else in the
  environment variable `NSQ_<NAME>`. Keys are never logged, stored in settings, or put in events.
"""
from __future__ import annotations

import json
import os
import ssl
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import urllib.robotparser
from pathlib import Path
from typing import Any

USER_AGENT = "NSKO-QUANT/0.3 (local personal research tool)"

# Minimum seconds between two requests to the same host (documented limits, rounded up).
HOST_MIN_INTERVAL = {
    "api.kraken.com": 1.0,              # public REST: ~1 req/s keeps well inside the counter
    "api.gdeltproject.org": 5.5,        # GDELT asks for at most one request every 5 s
    "export.arxiv.org": 3.1,            # arXiv API terms: one request every 3 s
    "api.github.com": 6.5,              # unauthenticated search: 10 requests/min
    "www.sec.gov": 0.15, "data.sec.gov": 0.15, "efts.sec.gov": 0.15,  # SEC: max 10 req/s
    "ll.thespacedevs.com": 240.0,       # Launch Library 2 free tier: 15 requests/hour
    "celestrak.org": 7200.0,            # CelesTrak asks GP data be fetched at most every 2 h
    "api.adsb.lol": 2.0,
    "earthquake.usgs.gov": 60.0,        # summary feeds update every minute
    "api.open-meteo.com": 1.0,
    "firms.modaps.eosdis.nasa.gov": 5.0,
    "planetarycomputer.microsoft.com": 1.0,
    "api.eia.gov": 1.0,
    "disclosures-clerk.house.gov": 5.0,
    "www.googleapis.com": 1.0,
}
DEFAULT_MIN_INTERVAL = 2.0

_lock = threading.Lock()
_last_call: dict[str, float] = {}
_blocked: dict[str, str] = {}       # host -> reason (network-level failure seen once)
_reachable: set[str] = set()
_robots: dict[str, urllib.robotparser.RobotFileParser | None] = {}


class Blocked(RuntimeError):
    """The host is unreachable (blocked network, DNS, proxy refusal). Use cache or synthetic data."""


def _ssl_ctx() -> ssl.SSLContext:
    cafile = os.environ.get("SSL_CERT_FILE") or os.environ.get("REQUESTS_CA_BUNDLE")
    return ssl.create_default_context(cafile=cafile) if cafile and Path(cafile).exists() else ssl.create_default_context()


def host_of(url: str) -> str:
    return urllib.parse.urlsplit(url).hostname or ""


def host_status() -> dict:
    with _lock:
        return {"reachable": sorted(_reachable), "blocked": dict(_blocked)}


def reset_host_status() -> None:
    with _lock:
        _blocked.clear(); _reachable.clear(); _last_call.clear(); _robots.clear()


def _wait_turn(host: str, min_interval: float | None) -> None:
    gap = HOST_MIN_INTERVAL.get(host, DEFAULT_MIN_INTERVAL) if min_interval is None else min_interval
    while True:
        with _lock:
            now = time.monotonic()
            last = _last_call.get(host)
            if last is None or now - last >= gap:
                _last_call[host] = now
                return
            wait = gap - (now - last)
        if wait > 30:  # never sleep for minutes inside a request; tell the caller to use cache
            raise Blocked(f"rate limit for {host}: next request allowed in {int(wait)} s")
        time.sleep(wait)


def robots_allowed(url: str) -> bool:
    """robots.txt check for page fetches (documented APIs are covered by their own terms)."""
    parts = urllib.parse.urlsplit(url)
    base = f"{parts.scheme}://{parts.netloc}"
    if base not in _robots:
        rp = urllib.robotparser.RobotFileParser()
        try:
            req = urllib.request.Request(base + "/robots.txt", headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=10, context=_ssl_ctx()) as r:
                rp.parse(r.read().decode("utf-8", "replace").splitlines())
        except urllib.error.HTTPError as e:
            rp.parse([] if e.code in (404, 410) else ["User-agent: *", "Disallow: /"])
        except Exception:
            rp = None
        _robots[base] = rp
    rp = _robots[base]
    return bool(rp and rp.can_fetch(USER_AGENT, url))


def _request(req: urllib.request.Request, timeout: float, min_interval: float | None, check_robots: bool) -> bytes:
    url = req.full_url
    host = host_of(url)
    with _lock:
        if host in _blocked:
            raise Blocked(f"{host} blocked: {_blocked[host]}")
    if check_robots and not robots_allowed(url):
        raise PermissionError(f"robots.txt disallows {url}")
    _wait_turn(host, min_interval)
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=_ssl_ctx()) as r:
            data = r.read()
        with _lock:
            _reachable.add(host)
        return data
    except urllib.error.HTTPError:
        with _lock:
            _reachable.add(host)  # the host answered; an HTTP error is not a network block
        raise
    except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as e:
        with _lock:
            _blocked[host] = type(e).__name__ + ": " + str(getattr(e, "reason", e))[:160]
        raise Blocked(f"{host} unreachable: {e}") from e


def http_get(url: str, params: dict | None = None, headers: dict | None = None, timeout: float = 20,
             min_interval: float | None = None, check_robots: bool = False) -> bytes:
    if params:
        url = url + ("&" if "?" in url else "?") + urllib.parse.urlencode(params, doseq=True)
    h = {"User-Agent": USER_AGENT, "Accept-Encoding": "identity"}
    h.update(headers or {})
    return _request(urllib.request.Request(url, headers=h), timeout, min_interval, check_robots)


def http_json(url: str, params: dict | None = None, headers: dict | None = None, **kw) -> Any:
    return json.loads(http_get(url, params, headers, **kw).decode("utf-8"))


def http_post_json(url: str, body: dict, headers: dict | None = None, timeout: float = 30,
                   min_interval: float | None = None) -> Any:
    h = {"User-Agent": USER_AGENT, "Content-Type": "application/json"}
    h.update(headers or {})
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers=h, method="POST")
    return json.loads(_request(req, timeout, min_interval, False).decode("utf-8"))


# ---------------------------------------------------------------------------------------------- db

def ensure_table(c, name: str, columns: dict[str, str], extra_sql: str = "") -> None:
    """Create `name` if missing; if it exists (perhaps created by another module) add missing
    columns. Column definitions added later must be nullable or have a default."""
    cols_sql = ", ".join(f"{k} {v}" for k, v in columns.items())
    c.execute(f"CREATE TABLE IF NOT EXISTS {name} ({cols_sql}{(', ' + extra_sql) if extra_sql else ''})")
    have = {r["name"] if isinstance(r, dict) else r[1] for r in c.execute(f"PRAGMA table_info({name})").fetchall()}
    for k, v in columns.items():
        if k not in have:
            v2 = v.replace("PRIMARY KEY", "").replace("AUTOINCREMENT", "").replace("NOT NULL", "")
            c.execute(f"ALTER TABLE {name} ADD COLUMN {k} {v2}")


def jdump(o: Any) -> str:
    return json.dumps(o, default=str, separators=(",", ":"))


def now_ms() -> int:
    return int(time.time() * 1000)


def cache_dir(*parts: str) -> Path:
    from nsq.db import data_dir
    p = Path(data_dir()).joinpath(*parts)
    p.mkdir(parents=True, exist_ok=True)
    return p


def secret(name: str) -> str | None:
    """Bring-your-own key lookup. Never echo the result."""
    for modname in ("nsq.keychain", "nsq.secrets", "nsq.vault"):
        try:
            mod = __import__(modname, fromlist=["get"])
            fn = getattr(mod, "get_secret", None) or getattr(mod, "get", None)
            if fn:
                v = fn(name)
                if v:
                    return str(v)
        except Exception:
            continue
    return os.environ.get("NSQ_" + name.upper().replace(".", "_").replace("-", "_")) or None


def setting(key: str, defaults: dict) -> Any:
    """`nsq.settings.get` with this package's default; works even before the db exists."""
    try:
        from nsq.settings import get
        return get(key, defaults.get(key))
    except Exception:
        return defaults.get(key)


def emit(type_: str, payload: dict) -> None:
    try:
        from nsq.bus import publish
        publish(type_, payload)
    except Exception:
        pass


def log(verb: str, msg: str) -> None:
    emit("ticker_log", {"verb": verb, "msg": msg})


def audit_safe(actor: str, action: str, detail: dict) -> None:
    try:
        from nsq.audit import audit
        audit(actor, action, detail)
    except Exception:
        pass


def safe_xml(data: bytes):
    """Parse untrusted XML. Uses defusedxml when installed; otherwise refuses any DTD
    (no DOCTYPE/ENTITY means no entity-expansion or external-entity tricks)."""
    try:
        from defusedxml.ElementTree import fromstring  # PSF licence
        return fromstring(data)
    except ImportError:
        import xml.etree.ElementTree as ET
        head = data[:4096].lower()
        if b"<!doctype" in head or b"<!entity" in data.lower():
            raise ValueError("XML with a DTD refused")
        return ET.fromstring(data)
