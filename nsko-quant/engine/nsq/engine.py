"""Engine runtime: starts the scheduler jobs, recovery and the demo source. Used by the FastAPI app."""
from __future__ import annotations

import threading
import time

from apscheduler.schedulers.background import BackgroundScheduler

from . import connectivity, health, notify
from .audit import audit
from .brokers import active
from .log import get as get_log
from .settings import get

_log = get_log("engine")


class Engine:
    def __init__(self):
        self.sched: BackgroundScheduler | None = None
        self.flow = None
        self.started = False
        self._scan_lock = threading.Lock()

    def start(self, scheduler: bool = True) -> None:
        if self.started:
            return
        self.started = True
        from .trading.flow import TradeFlow
        self.flow = TradeFlow(active())
        how = health.keep_awake(True)
        try:
            import os
            from .db import data_dir
            (data_dir() / "engine.pid").write_text(str(os.getpid()))
        except OSError:
            pass
        audit("engine", "engine.start", {"keep_awake": how, "broker": active().name, "mode": get("mode")})
        try:
            from .recovery import reconcile
            reconcile(active())
        except Exception as e:
            _log.error(f"reconcile on start failed: {e}")
        if get("demo") and active().name == "paper" and not get("data.connected", False):
            from .demo import source
            source.start()
        if scheduler:
            s = BackgroundScheduler(timezone="UTC", job_defaults={"coalesce": True, "max_instances": 1, "misfire_grace_time": 5})
            s.add_job(health.beat, "interval", seconds=1, id="health")
            s.add_job(lambda: connectivity.check(active()), "interval", seconds=10, id="net")
            s.add_job(notify.poll_telegram, "interval", seconds=5, id="telegram")
            s.add_job(notify.daily_summary, "cron", hour=21, minute=17, id="daily_summary")
            s.add_job(self.scan, "cron", second=5, id="scan")       # once a minute, just after bars close
            s.add_job(self.manage_prices, "interval", seconds=5, id="manage")
            s.start()
            self.sched = s

    def scan(self) -> list:
        if not self._scan_lock.acquire(blocking=False):
            return []
        try:
            from .trading.strategies import approved
            out = []
            for s in approved():
                try:
                    out.append(self.flow.run(s))
                except Exception as e:
                    _log.error(f"flow error on {s['id']}: {e}")
                    notify.notify("error", "Engine error", f"{s['id']}: {type(e).__name__}", level="error")
            return out
        finally:
            self._scan_lock.release()

    def manage_prices(self) -> None:
        if not self.flow or not self.flow.manager.tracked:
            return
        for m in {t["plan"]["market"] for t in self.flow.manager.tracked.values()}:
            try:
                b = active()
                if hasattr(b, "set_price"):
                    from .data import candles
                    df = candles.latest(m, "1m", 2)
                    self.flow.on_price(m, float(df["close"].iloc[-1]), float(df["high"].iloc[-1]), float(df["low"].iloc[-1]))
                else:
                    self.flow.on_price(m, b.ticks(m)["price"])
            except Exception as e:
                _log.warning(f"manage price for {m} failed: {type(e).__name__}")

    def stop(self) -> None:
        if self.sched:
            self.sched.shutdown(wait=False)
        from .demo import source
        source.stop()
        health.keep_awake(False)
        audit("engine", "engine.stop", {"uptime": round(time.time() - health.STARTED)})
        self.started = False


engine = Engine()
