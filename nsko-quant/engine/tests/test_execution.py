"""Bracket placement (native + fallback), idempotent retries, sizing rounding, kill switch, partial close,
reboot recovery, internet drop, withdraw helper."""
import pytest

from nsq.brokers.base import round_down, value_per_point
from nsq.brokers.paper import PaperBroker
from nsq.trading.execute import execute_bracket
from nsq.trading.sizing import size_trade

PLAN = {"id": "abc123", "market": "XAU/USD", "side": "buy", "qty": 0.21, "stop": 2644.0, "target": 2659.6, "entry": 2650.0}


def test_native_bracket(paper):
    r = execute_bracket(paper, PLAN, sleep=lambda s: None)
    assert r["ok"] and r["path"] == "native"
    [p] = paper.positions()
    assert p.stop == 2644.0 and p.target == 2659.6
    roles = sorted(o.role for o in paper.orders())
    assert roles == ["stop", "target"]
    assert r["fill_price"] > 2650.0, "buy fills at the ask plus slippage"


def test_bracket_retry_is_idempotent(paper):
    execute_bracket(paper, PLAN, sleep=lambda s: None)
    execute_bracket(paper, PLAN, sleep=lambda s: None)   # same plan id -> same client order ids
    assert len(paper.positions()) == 1
    assert len(paper.orders()) == 2


def test_fallback_places_and_verifies_both_legs():
    b = PaperBroker(start_balance=10000, native_brackets=False)
    b.set_price("XAU/USD", 2650.0)
    r = execute_bracket(b, PLAN, sleep=lambda s: None)
    assert r["ok"] and r["path"] == "fallback" and r["verified"] == {"stop": True, "target": True}
    [p] = b.positions()
    assert p.stop_order_id and p.target_order_id


def test_fallback_closes_position_if_stop_cannot_be_placed():
    b = PaperBroker(start_balance=10000, native_brackets=False)
    b.set_price("XAU/USD", 2650.0)
    b.fail_roles = {"stop"}
    r = execute_bracket(b, PLAN, sleep=lambda s: None)
    assert not r["ok"] and r["closed_for_safety"]
    assert b.positions() == [], "never leave a position without a stop"


def test_fallback_retries_a_flaky_target():
    b = PaperBroker(start_balance=10000, native_brackets=False)
    b.set_price("XAU/USD", 2650.0)
    calls = {"n": 0}
    orig = b._rest

    def flaky(p, role, price, cid):
        if role == "target" and calls["n"] == 0:
            calls["n"] += 1
            from nsq.brokers.base import BrokerError
            raise BrokerError("timeout")
        return orig(p, role, price, cid)
    b._rest = flaky
    r = execute_bracket(b, PLAN, sleep=lambda s: None)
    assert r["ok"] and r["retries"] >= 1
    assert len([o for o in b.orders() if o.role == "stop"]) == 1, "retry did not duplicate the stop"


def test_sizing_rounds_down_to_broker_step():
    vpp = value_per_point("XAU/USD")          # 100 oz x 0.79 GBP
    s = size_trade(10000, 1.0, 2650.0, 2644.0, "XAU/USD")
    raw = 100 / (6.0 * vpp)
    assert s["raw_qty"] == pytest.approx(raw)
    assert s["qty"] == 0.21 and s["qty"] <= raw
    assert s["risk_at_stop"] <= 100
    assert round_down(0.2199999, 0.01) == 0.21
    assert round_down(7.9, 1) == 7
    assert size_trade(10000, 1.0, 141.2, 141.0, "NVDA")["qty"] == 632   # whole shares
    tiny = size_trade(100, 1.0, 2650.0, 2600.0, "XAU/USD")
    assert tiny["qty"] == 0.0 and "minimum" in tiny["reason"]
    assert size_trade(10000, 1.0, 2650.0, 2644.0, "XAU/USD", size_factor=0.5)["qty"] == 0.1


def test_partial_close_and_stop_target_fills(paper):
    execute_bracket(paper, PLAN, sleep=lambda s: None)
    [p] = paper.positions()
    r = paper.close(p.id, 0.1)
    assert not r["full"] and r["remaining_qty"] == pytest.approx(0.11)
    assert all(o.qty == pytest.approx(0.11) for o in paper.orders()), "legs resized after partial close"
    ev = paper.set_price("XAU/USD", 2660.5)
    assert ev and ev[0]["reason"] == "target" and paper.positions() == []
    assert paper.orders() == [], "OCO: the stop was cancelled when the target filled"


def test_stop_fill_has_slippage(paper):
    execute_bracket(paper, PLAN, sleep=lambda s: None)
    ev = paper.set_price("XAU/USD", 2640.0)          # gaps through the stop
    assert ev[0]["reason"] == "stop" and ev[0]["price"] <= 2644.0
    assert ev[0]["pnl"] < -100 * 0.79 * 0.21 * 6 * 0.9


def test_kill_switch_closes_everything_and_locks(paper):
    from nsq.bus import recent
    from nsq.trading.killswitch import enable, is_locked, kill
    execute_bracket(paper, PLAN, sleep=lambda s: None)
    paper.set_price("BTC/USD", 97000)
    execute_bracket(paper, {**PLAN, "id": "btc1", "market": "BTC/USD", "qty": 0.01, "stop": 96000, "target": 98600}, sleep=lambda s: None)
    assert len(paper.positions()) == 2
    r = kill("test")
    assert r["closed"] == 2 and r["cancelled"] == 4
    assert paper.positions() == [] and paper.orders() == []
    assert is_locked()[0]
    assert recent("kill_switch")[-1]["payload"]["on"] is True
    enable()
    assert not is_locked()[0]


def test_kill_endpoint_and_telegram_paired_only(paper):
    from fastapi.testclient import TestClient
    from nsq.app import create_app
    from nsq.notify import handle_telegram_update
    from nsq.settings import get, set as sset
    c = TestClient(create_app(start_engine=False))
    assert c.post("/kill").status_code == 403, "POST needs the X-NSQ-Client header"
    assert c.post("/kill", headers={"X-NSQ-Client": "app"}).json()["locked"] is True
    sset("trading.locked", False)
    sset("notify.telegram_chat_id", "1111")
    assert handle_telegram_update({"message": {"chat": {"id": 2222}, "text": "/kill"}}) == "refused"
    assert get("trading.locked") is False
    assert handle_telegram_update({"message": {"chat": {"id": 1111}, "text": "/kill"}}) == "killed"
    assert get("trading.locked") is True


def test_reboot_recovery_replaces_missing_stop(paper):
    from nsq.recovery import reconcile
    execute_bracket(paper, PLAN, sleep=lambda s: None)
    [p] = paper.positions()
    paper.cancel(p.stop_order_id)                     # stop lost (e.g. broker-side expiry before the reboot)
    rebooted = PaperBroker()                          # new process: state comes back from the database
    rebooted.set_price("XAU/USD", 2650.0)
    [p2] = rebooted.positions()
    assert p2.stop_order_id is None and p2.target_order_id
    rep = reconcile(rebooted)
    assert any(x["leg"] == "stop" for x in rep["replaced"])
    [p3] = rebooted.positions()
    assert p3.stop_order_id and p3.stop is not None and p3.target_order_id


def test_internet_drop_stops_entries_keeps_stops(paper):
    from nsq import connectivity
    from nsq.trading import risk
    execute_bracket(paper, PLAN, sleep=lambda s: None)
    paper.connected = False
    st = connectivity.check(paper)
    assert st["online"] is False or paper.connected is True
    paper.connected = False
    ctx = risk.TradeContext("x", "XAU/USD", "buy", 2650, 2644, 2659, 0.1, 50, 10000, 2649.9, 2650.1,
                            __import__("time").time(), paper.online() and connectivity.is_online())
    assert "broker_online" in risk.check(ctx).blocked_by
    ev = paper.set_price("XAU/USD", 2643.0)            # broker-side stop still protects while offline
    assert ev and ev[0]["reason"] == "stop"


def test_withdraw_helper_is_information_only(paper):
    from nsq.trading.withdraw import helper
    h = helper(paper)
    assert h["paper"] and h["free_to_withdraw"] == pytest.approx(10000)
    import nsq
    import pathlib
    src = "\n".join(p.read_text() for p in pathlib.Path(nsq.__file__).parent.rglob("*.py")
                    if "research" not in p.parts and "data" not in p.parts)
    for forbidden in ("private/Withdraw", "withdrawals/crypto", "def withdraw(", "/v2/transfers", "/transfers\"", "send_money"):
        assert forbidden not in src, f"withdrawal code found: {forbidden}"
