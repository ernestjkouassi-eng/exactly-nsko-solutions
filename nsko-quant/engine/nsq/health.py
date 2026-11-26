"""Engine health: uptime, last heartbeat, CPU, RAM (psutil), keep-awake state.

`beat()` runs every second (scheduler) and publishes `engine_health`. It also writes a heartbeat file
that the watchdog reads (<data_dir>/heartbeat).
"""
from __future__ import annotations

import os
import sys
import time

import psutil

from .bus import publish
from .db import data_dir

STARTED = time.time()
_state = {"round": 0, "heartbeat": None, "keep_awake": False, "keep_awake_how": None}
_proc = psutil.Process(os.getpid())
_proc.cpu_percent(None)


def trading_state() -> dict:
    """Kill switch and pause, for /health, the engine_health event and the tray colour."""
    try:
        from .settings import get
        from .trading.killswitch import is_locked
        locked, why = is_locked()
        return {"killed": bool(get("trading.locked", False)), "locked": locked, "lock_reason": why,
                "paused": bool(get("trading.paused", False))}
    except Exception:   # the database is not ready yet: report nothing rather than guess
        return {}


def snapshot() -> dict:
    mem = _proc.memory_info().rss / 1e9
    return {"status": "running", **trading_state(), "uptime": round(time.time() - STARTED, 1), "round": _state["round"],
            "heartbeat": _state["heartbeat"], "cpu": psutil.cpu_percent(None), "cpu_engine": _proc.cpu_percent(None),
            "ram": round(psutil.virtual_memory().used / 1e9, 2), "ram_engine": round(mem, 3),
            "ram_total": round(psutil.virtual_memory().total / 1e9, 2), "keepAwake": _state["keep_awake"],
            "keep_awake_how": _state["keep_awake_how"], "pid": os.getpid(), "platform": sys.platform}


def beat() -> dict:
    _state["round"] += 1
    _state["heartbeat"] = int(time.time() * 1000)
    s = snapshot()
    publish("engine_health", s)
    try:
        (data_dir() / "heartbeat").write_text(str(_state["heartbeat"]))
    except OSError:
        pass
    return s


# ------------------------------------------------------------------ keep-awake
ES_CONTINUOUS, ES_SYSTEM_REQUIRED, ES_AWAYMODE_REQUIRED = 0x80000000, 0x00000001, 0x00000040
_inhibitor = None


def keep_awake(on: bool = True) -> str:
    """Stop the computer sleeping while the engine runs.
    Windows: SetThreadExecutionState(ES_CONTINUOUS | ES_SYSTEM_REQUIRED | ES_AWAYMODE_REQUIRED).
    macOS: `caffeinate -i -w <pid>` (the launchd plist also wraps the engine in caffeinate).
    Linux: `systemd-inhibit` (the systemd unit wraps the engine; this is the fallback when run by hand)."""
    global _inhibitor
    how = "none"
    try:
        if sys.platform == "win32":
            import ctypes
            flags = (ES_CONTINUOUS | ES_SYSTEM_REQUIRED | ES_AWAYMODE_REQUIRED) if on else ES_CONTINUOUS
            ctypes.windll.kernel32.SetThreadExecutionState(flags)  # type: ignore[attr-defined]
            how = "SetThreadExecutionState"
        elif sys.platform == "darwin":
            import subprocess
            if on and _inhibitor is None:
                _inhibitor = subprocess.Popen(["caffeinate", "-i", "-w", str(os.getpid())])
            how = "caffeinate"
        else:
            import shutil
            import subprocess
            if os.environ.get("NSQ_INHIBITED") == "1":
                how = "systemd-inhibit (service)"
            elif on and _inhibitor is None and shutil.which("systemd-inhibit"):
                _inhibitor = subprocess.Popen(["systemd-inhibit", "--what=sleep:idle", "--who=NSKO QUANT",
                                               "--why=trading engine running", "--mode=block",
                                               "tail", f"--pid={os.getpid()}", "-f", "/dev/null"],   # ends with the engine
                                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                how = "systemd-inhibit"
                time.sleep(0.3)
                if _inhibitor.poll() is not None:   # no logind / D-Bus (containers): it exits at once
                    _inhibitor, how = None, "failed: systemd-inhibit unavailable"
        if not on and _inhibitor is not None:
            _inhibitor.terminate()
            _inhibitor = None
    except Exception as e:
        how = f"failed: {type(e).__name__}"
    _state["keep_awake"] = on and not how.startswith(("none", "failed"))
    _state["keep_awake_how"] = how
    return how
