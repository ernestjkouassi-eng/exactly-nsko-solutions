"""Every risk-gate block, and that the gate cannot be switched off in live."""
import time

import pytest

from nsq.db import conn
from nsq.settings import set as sset
from nsq.trading import risk
from nsq.trading.risk import TradeContext


def ctx(**kw):
    base = dict(plan_id="p1", market="XAU/USD", side="buy", entry=2650.0, stop=2644.0, target=2659.6, qty=0.21,
                risk_gbp=99.5, equity=10000.0, bid=2649.85, ask=2650.15, last_data_ts=time.time() - 5,
                broker_online=True, data_ok=True, open_positions=[], mode="paper")
    base.update(kw)
    return TradeContext(**base)


def test_clean_trade_passes():
    r = risk.check(ctx())
    assert r.passed, r.blocked_by
    assert conn().execute("SELECT COUNT(*) n FROM risk_events WHERE rule='all' AND passed=1").fetchone()["n"] == 1


def _blocked(c, rule):
    r = risk.check(c)
    assert not r.passed
    assert rule in r.blocked_by, r.blocked_by
    row = conn().execute("SELECT * FROM risk_events WHERE rule=? AND passed=0", (rule,)).fetchone()
    assert row and row["reason"], "every block is logged with its reason"
    return r


def test_per_trade_risk_over_1pct():
    _blocked(ctx(risk_gbp=150.0), "per_trade_risk")


def test_daily_loss_3pct_stops_for_the_day():
    conn().execute("INSERT INTO journal (ts, pnl, mode) VALUES (?,?,?)", (time.time(), -310.0, "paper"))
    _blocked(ctx(), "daily_loss")
    from nsq.trading.killswitch import is_locked
    assert is_locked()[0], "daily loss locks trading for the rest of the day"


def test_weekly_loss_6pct():
    import datetime as dt
    now = dt.datetime.now(dt.timezone.utc)
    monday = (now - dt.timedelta(days=now.weekday())).replace(hour=0, minute=1, second=0, microsecond=0)
    # a loss earlier this week but not today (unless today is Monday: then use the current moment)
    ts = monday.timestamp() if now.weekday() > 0 else time.time()
    conn().execute("INSERT INTO journal (ts, pnl, mode) VALUES (?,?,?)", (ts, -610.0, "paper"))
    r = risk.check(ctx())
    assert "weekly_loss" in r.blocked_by


def test_max_5_trades_a_day():
    for i in range(5):
        conn().execute("INSERT INTO trade_plans (id, market, state, mode, created_at, updated_at) VALUES (?,?,?,?,?,?)",
                       (f"t{i}", "XAU/USD", "closed", "paper", time.time(), time.time()))
    _blocked(ctx(), "max_trades_day")


def test_max_2_open_positions():
    _blocked(ctx(open_positions=[{"market": "BTC/USD", "risk_gbp": 50}, {"market": "ETH/USD", "risk_gbp": 50}]),
             "max_open_positions")


def test_max_exposure_per_market():
    _blocked(ctx(open_positions=[{"market": "XAU/USD", "risk_gbp": 150}]), "market_exposure")


def test_stale_data_blocks():
    _blocked(ctx(last_data_ts=time.time() - 3600), "fresh_data")


def test_broker_offline_blocks():
    _blocked(ctx(broker_online=False), "broker_online")


def test_spread_too_wide_blocks():
    _blocked(ctx(bid=2640.0, ask=2660.0), "spread")
    sset("risk.max_spread_points", {"XAU/USD": 0.2})
    _blocked(ctx(bid=2649.8, ask=2650.2), "spread")


def test_missing_stop_blocks():
    _blocked(ctx(stop=None), "stop_and_target")


def test_zero_size_blocks():
    _blocked(ctx(qty=0.0), "size_positive")


def test_kill_switch_lock_blocks():
    sset("trading.locked", True)
    _blocked(ctx(), "trading_unlocked")


def test_gate_can_be_disabled_in_paper_but_never_in_live():
    sset("risk.gate_enabled", False)
    assert risk.check(ctx(risk_gbp=500.0)).passed, "paper experiments may switch the gate off"
    r = risk.check(ctx(risk_gbp=500.0, mode="live"))
    assert not r.passed and "per_trade_risk" in r.blocked_by


def test_live_limits_cannot_exceed_hard_caps():
    sset("risk.per_trade_pct", 50.0)
    sset("risk.max_exposure_per_market_pct", 50.0)
    assert risk.check(ctx(risk_gbp=1000.0, mode="paper")).passed is True
    r = risk.check(ctx(risk_gbp=1000.0, mode="live"))
    assert "per_trade_risk" in r.blocked_by   # capped at 2% in live


def test_settings_api_refuses_gate_off_in_live():
    from fastapi.testclient import TestClient
    from nsq import account
    from nsq.app import create_app
    c = TestClient(create_app(start_engine=False))
    tok = account.create("e@example.com", "a-long-password")["token"]
    sset("mode", "live")
    r = c.post("/settings", json={"key": "risk.gate_enabled", "value": False},
               headers={"Authorization": f"Bearer {tok}", "X-NSQ-Client": "test"})
    assert r.status_code == 400
    r = c.post("/settings", json={"key": "mode", "value": "live"}, headers={"Authorization": f"Bearer {tok}", "X-NSQ-Client": "t"})
    assert r.status_code == 400


def test_risk_check_event_published():
    from nsq.bus import recent
    risk.check(ctx(risk_gbp=999))
    ev = recent("risk_check")[-1]
    assert ev["payload"]["passed"] is False and "per_trade_risk" in ev["payload"]["blocked_by"]
