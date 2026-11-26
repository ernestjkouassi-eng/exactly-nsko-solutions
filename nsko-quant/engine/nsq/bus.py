"""In-process event bus (CONTRACT.md).

`publish(type, payload)` is synchronous and thread-safe. Subscribers are plain callables
that receive `{"type", "ts" (ms), "payload"}`. The WebSocket `/ws` endpoint subscribes and
broadcasts every event. A short ring buffer keeps recent events for late joiners and tests.
"""
from __future__ import annotations

import threading
import time
from collections import deque
from typing import Callable

EVENT_TYPES = frozenset("""
tick candle orderflow_bubble profile_update ticker_log agent_status agent_handoff source_added
summary_done term_found recipe_created variant_tested backtest_done strategy_status decision_needed
scan_hit news_hit forecast_done entry_state timemachine_progress timemachine_done size_calc
risk_check order_sent order_filled position_update exit_done alert gods_eye_event market_impact
kill_switch engine_health budget_update
""".split())

_lock = threading.RLock()
_subs: list[Callable[[dict], None]] = []
_recent: deque = deque(maxlen=2000)


def publish(type: str, payload: dict) -> dict:  # noqa: A002 - name fixed by the contract
    """Publish one event to every subscriber. Never raises because of a bad subscriber."""
    if type not in EVENT_TYPES:
        # Unknown names are still delivered (forward compatible), but flagged for the logs.
        payload = {**payload, "_unknown_type": True}
    ev = {"type": type, "ts": int(time.time() * 1000), "payload": payload}
    with _lock:
        _recent.append(ev)
        subs = list(_subs)
    for fn in subs:
        try:
            fn(ev)
        except Exception:  # a broken subscriber must not break the publisher
            pass
    return ev


def subscribe(fn: Callable[[dict], None]) -> Callable[[], None]:
    """Register a subscriber. Returns an unsubscribe function."""
    with _lock:
        _subs.append(fn)

    def _unsub() -> None:
        with _lock:
            if fn in _subs:
                _subs.remove(fn)

    return _unsub


def recent(type: str | None = None, n: int = 200) -> list[dict]:  # noqa: A002
    with _lock:
        evs = list(_recent)
    if type:
        evs = [e for e in evs if e["type"] == type]
    return evs[-n:]


def clear_recent() -> None:
    with _lock:
        _recent.clear()
