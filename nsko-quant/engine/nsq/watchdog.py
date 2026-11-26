"""Watchdog: `python -m nsq.watchdog`.

The OS service manager (systemd / launchd / NSSM) restarts the engine if the PROCESS dies. The watchdog
catches the other failure: the process is alive but stuck. Every 15 s it checks GET /health and the
heartbeat file. If both are stale for 60 s it kills the engine process (the service manager restarts it),
or, if run with --spawn, starts the engine itself and restarts it.
"""
from __future__ import annotations

import argparse
import os
import signal
import subprocess
import sys
import time
import urllib.request

from .db import data_dir


def healthy(url: str, stale_s: float) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=5) as r:
            if r.status == 200:
                return True
    except Exception:
        pass
    try:
        hb = int((data_dir() / "heartbeat").read_text()) / 1000
        return time.time() - hb < stale_s
    except Exception:
        return False


def main() -> None:
    ap = argparse.ArgumentParser(prog="nsq.watchdog")
    ap.add_argument("--url", default="http://127.0.0.1:8787/health")
    ap.add_argument("--every", type=float, default=15)
    ap.add_argument("--stale", type=float, default=60)
    ap.add_argument("--pid", type=int, help="engine pid to kill when stuck (default: <data_dir>/engine.pid)")
    ap.add_argument("--spawn", action="store_true", help="start and supervise the engine itself")
    a = ap.parse_args()
    proc = None
    bad_since = None
    while True:
        if a.spawn and (proc is None or proc.poll() is not None):
            proc = subprocess.Popen([sys.executable, "-m", "nsq"])
            time.sleep(10)
        ok = healthy(a.url, a.stale)
        if ok:
            bad_since = None
        else:
            bad_since = bad_since or time.time()
            if time.time() - bad_since >= a.stale:
                pid = proc.pid if proc else a.pid
                if not pid:
                    try:
                        pid = int((data_dir() / "engine.pid").read_text())
                    except Exception:
                        pid = None
                print(f"watchdog: engine unhealthy for {a.stale:.0f}s, restarting (pid {pid})", flush=True)
                if pid:
                    try:
                        os.kill(pid, signal.SIGTERM if sys.platform != "win32" else signal.SIGTERM)
                    except OSError:
                        pass
                bad_since = None
                time.sleep(5)
        time.sleep(a.every)


if __name__ == "__main__":
    main()
