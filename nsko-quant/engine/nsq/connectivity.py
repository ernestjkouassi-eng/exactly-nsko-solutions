"""Internet-drop handling.

A scheduled job probes the network and the broker. When the connection drops:
  - new entries stop (the risk gate's broker_online check fails),
  - nothing is cancelled: stops and targets already sit at the broker (broker-side), so they keep protecting,
  - the engine retries the broker connection with backoff until it is back, then reconciles.
"""
from __future__ import annotations

import socket
import threading
import time

from .bus import publish
from .log import get as get_log

_log = get_log("net")
_state = {"online": True, "since": time.time(), "fails": 0, "next_try": 0.0, "forced": None}
_lock = threading.Lock()


def is_online() -> bool:
    with _lock:
        if _state["forced"] is not None:
            return bool(_state["forced"])
        return bool(_state["online"])


def force(online: bool | None) -> None:
    """Tests / manual: force the state (None = back to probing)."""
    with _lock:
        _state["forced"] = online


def probe_internet(hosts=(("1.1.1.1", 53), ("8.8.8.8", 53)), timeout: float = 2.0) -> bool:
    for h, p in hosts:
        try:
            with socket.create_connection((h, p), timeout=timeout):
                return True
        except OSError:
            continue
    return False


def check(broker=None, probe=probe_internet) -> dict:
    """One monitoring tick. Safe to call every few seconds."""
    from .brokers import active
    b = broker or active()
    net = True if b.name == "paper" else probe()
    ok = net and b.online()
    now = time.time()
    with _lock:
        was = _state["online"]
        if not ok:
            _state["fails"] += 1
        _state["online"] = ok
        if ok != was:
            _state["since"] = now
    if was and not ok:
        _log.warning("connection lost: new entries stopped, broker-side stops stay in place")
        publish("alert", {"kind": "error", "level": "error", "title": "Connection lost",
                          "body": "New entries are stopped. Your stops and targets stay at the broker. Reconnecting."})
    if not ok and now >= _state["next_try"]:
        try:
            b.connect()
            with _lock:
                _state.update(online=True, fails=0, since=now)
            publish("alert", {"kind": "info", "level": "info", "title": "Reconnected", "body": "Checking positions with the broker."})
            from .recovery import reconcile
            reconcile(b)
        except Exception:
            delay = min(300, 2 ** min(_state["fails"], 8))
            _state["next_try"] = now + delay
    elif ok and not was:
        from .recovery import reconcile
        reconcile(b)
    return {"online": is_online(), "fails": _state["fails"], "since": _state["since"]}
