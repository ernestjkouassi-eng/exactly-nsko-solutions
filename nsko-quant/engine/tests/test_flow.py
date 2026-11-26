"""End-to-end paper trade, auto vs manual, NO-LOOK-AHEAD, strategy updates and rollback, demo source, API."""
import threading
import time

import pandas as pd
import pytest

from conftest import trend_candles
from nsq.bus import recent
from nsq.db import conn
from nsq.settings import set as sset
from nsq.trading import strategies as st
from nsq.trading.flow import TradeFlow, approve, closed_bars

RECIPE = {"id": "trend-xau", "name": "Trend-XAU", "market": "XAU/USD", "timeframe": "15m", "idea_type": "Trend following",
          "entry": {"type": "test_last_bar"}, "stop": {"type": "atr", "mult": 1.0}, "target": {"type": "r", "r": 2.0},
          "filters": {"session": ["london", "ny"], "news_blackout_min": 15}, "params": {}}


def last_bar_signal(recipe, df):
    """Test generator: a long on the LAST CLOSED bar, stop 1 ATR below, target 2R. Closed bars only."""
    tr = (df["high"] - df["low"]).rolling(14).mean()
    a = float(tr.iloc[-1])
    e = float(df["close"].iloc[-1])
    return [{"time": df.index[-1], "side": "buy", "entry": e, "stop": e - a * 2, "target": e + a * 4, "reason": "test"}]


NOW = pd.Timestamp("2026-11-24 10:16", tz="UTC")   # the 10:00 bar closed at 10:15


@pytest.fixture
def strategy(paper):
    sid = st.create(RECIPE, status="paper")
    return st.approved()[0]


def run_flow(paper, strategy, **kw):
    df = trend_candles()
    flow = TradeFlow(paper, signals_fn=last_bar_signal, use_llm=False)
    paper.set_price("XAU/USD", float(df["close"].iloc[-1]), ts=NOW.timestamp())
    return flow, flow.run(strategy, now=NOW, df=df, **kw), df


def test_end_to_end_paper_trade(paper, strategy):
    sset("forecast.paths", 400)
    sset("timemachine.replays", 2000)
    flow, r, df = run_flow(paper, strategy)
    assert r["result"] == "executed", r
    assert r["steps"] == ["scanner", "news", "forecast", "entry", "timemachine", "size", "risk", "debate", "execute", "manage"]
    for ev in ("scan_hit", "news_hit", "forecast_done", "entry_state", "timemachine_progress", "timemachine_done",
               "size_calc", "risk_check", "order_sent", "order_filled", "alert"):
        assert recent(ev), f"missing event {ev}"
    assert r["forecast"]["engine"] == "block-bootstrap fallback"
    tm = r["timemachine"]
    assert tm["p_target"] + tm["p_stop"] + tm["p_open"] == pytest.approx(100, abs=0.2)
    [p] = paper.positions()
    assert p.stop_order_id and p.target_order_id
    plan = r["plan"]
    entry, stop, target = r["execution"]["fill_price"], plan["stop"], plan["target"]
    # manage: price reaches 1R -> scale out 50% and stop to breakeven
    one_r = entry + (entry - stop) * 1.05
    flow.on_price("XAU/USD", one_r, now=NOW.timestamp() + 60)
    [p] = paper.positions()
    assert p.qty < plan["qty"] and p.stop == pytest.approx(entry)
    assert any(e["payload"].get("event") == "scale_out" for e in recent("position_update"))
    # exit at target -> journal + alert
    exits = flow.on_price("XAU/USD", target + 1, now=NOW.timestamp() + 120)
    assert exits and exits[0]["reason"] == "target" and exits[0]["pnl"] > 0
    j = conn().execute("SELECT * FROM journal").fetchall()
    assert len(j) == 1 and j[0]["mode"] == "paper"
    assert recent("exit_done")[-1]["payload"]["pnl"] > 0
    assert conn().execute("SELECT state FROM trade_plans WHERE id=?", (r["plan_id"],)).fetchone()["state"] == "closed"


def test_news_blackout_skips(paper, strategy):
    sset("news.events", [{"time": (NOW + pd.Timedelta(minutes=10)).isoformat(), "impact": "high", "title": "US CPI", "currency": "USD"}])
    _, r, _ = run_flow(paper, strategy)
    assert r["result"] == "skipped" and r["step"] == "news" and "CPI" in r["why"]
    sset("news.events", [{"time": (NOW + pd.Timedelta(minutes=40)).isoformat(), "impact": "high", "title": "US CPI", "currency": "USD"}])
    _, r, _ = run_flow(paper, strategy)
    assert r.get("step") != "news"


def test_unapproved_strategy_is_not_scanned(paper):
    st.create({**RECIPE, "id": "lab-only"})
    s = {**st.get_strategy("lab-only"), "recipe": st.recipe("lab-only")}
    r = TradeFlow(paper, signals_fn=last_bar_signal).run(s, now=NOW, df=trend_candles())
    assert r["result"] == "skipped" and r["step"] == "scanner"


def test_manual_mode_timeout_defaults_to_skip(paper, strategy):
    sset("trade_mode", "manual")
    sset("timemachine.replays", 1000)
    _, r, _ = run_flow(paper, strategy, manual_timeout_s=0.3)
    assert r["result"] == "skipped" and r["step"] == "execute" and "default: skip" in r["why"]
    assert paper.positions() == []
    assert recent("decision_needed")


def test_manual_mode_approve_executes(paper, strategy):
    sset("trade_mode", "manual")
    sset("timemachine.replays", 1000)

    def approver():
        for _ in range(200):
            ev = recent("decision_needed")
            if ev and approve(ev[-1]["payload"]["id"], "approve"):
                return
            time.sleep(0.02)
    t = threading.Thread(target=approver)
    t.start()
    _, r, _ = run_flow(paper, strategy, manual_timeout_s=10)
    t.join()
    assert r["result"] == "executed"
    assert len(paper.positions()) == 1


def test_auto_mode_does_not_wait(paper, strategy):
    sset("trade_mode", "auto")
    sset("timemachine.replays", 1000)
    t0 = time.time()
    _, r, _ = run_flow(paper, strategy, manual_timeout_s=30)
    assert r["result"] == "executed" and time.time() - t0 < 20
    assert not recent("decision_needed")


def test_killed_flow_does_not_trade(paper, strategy):
    from nsq.trading.killswitch import kill
    kill("test")
    sset("timemachine.replays", 1000)
    _, r, _ = run_flow(paper, strategy)
    assert r["result"] == "skipped" and r["step"] == "risk"


# ------------------------------------------------------------------ NO LOOK-AHEAD
def test_no_look_ahead_closed_bars_only(paper, strategy):
    """1) The forming bar is dropped before signals and entry. 2) Changing the forming bar, or any future
    bar, cannot change a signal or the entry decision. 3) Signals at bar t are identical whether or not
    later bars exist (for the lab generator if installed, and for the fallback generator)."""
    df = trend_candles(n=401)                          # last bar (10:00) is still forming at 10:10
    now = pd.Timestamp("2026-11-24 10:10", tz="UTC")
    cb = closed_bars(df, "15m", now)
    assert len(cb) == 400 and cb.index[-1] == df.index[-2]
    seen = []

    def spy(recipe, d):
        seen.append(d.index[-1])
        return last_bar_signal(recipe, d)
    flow = TradeFlow(paper, signals_fn=spy)
    sset("timemachine.replays", 500)
    paper.set_price("XAU/USD", float(df["close"].iloc[-2]), ts=now.timestamp())
    flow.run(strategy, now=now, df=df)
    assert seen and seen[-1] == df.index[-2], "signals never see the forming bar"
    # a wild forming bar must not change what the scanner sees
    df2 = df.copy()
    df2.iloc[-1, df2.columns.get_loc("close")] *= 1.5
    df2.iloc[-1, df2.columns.get_loc("high")] *= 1.5
    pd.testing.assert_frame_equal(closed_bars(df2, "15m", now), cb)

    gens = []
    from nsq.trading import signals_fallback
    gens.append(("fallback", signals_fallback.generate, {**RECIPE, "entry": {"type": "ema_cross", "fast": 5, "slow": 13}}))
    try:
        from nsq.lab import signals as lab_signals
        gens.append(("lab", lab_signals.generate, {**RECIPE, "entry": {"type": "ema_cross", "fast": 5, "slow": 13}}))
    except Exception:
        pass
    full = trend_candles(n=600, drift=0.0, vol=0.002, seed=11)
    for name, gen, rec in gens:
        all_sigs = gen(rec, full)
        cut = full.index[400]
        early = gen(rec, full[full.index <= cut])
        key = lambda s: (pd.Timestamp(s["time"]), s["side"], round(float(s["entry"]), 6), round(float(s["stop"]), 6))  # noqa: E731
        assert [key(s) for s in all_sigs if pd.Timestamp(s["time"]) <= cut] == [key(s) for s in early], name
        assert all(pd.Timestamp(s["time"]) <= cut for s in early)


def test_entry_uses_live_quote_not_signal_bar(paper, strategy):
    sset("timemachine.replays", 1000)
    df = trend_candles()
    paper.set_price("XAU/USD", float(df["close"].iloc[-1]) + 1.0, ts=NOW.timestamp())
    r = TradeFlow(paper, signals_fn=last_bar_signal).run(strategy, now=NOW, df=df)
    assert r["result"] == "executed"
    assert r["plan"]["entry"] == pytest.approx(paper.quotes["XAU/USD"]["ask"])


# ------------------------------------------------------------------ strategy updates
def test_strategy_versions_promote_and_rollback(paper):
    sid = st.create(RECIPE, status="paper")
    v2 = st.manual_update(sid, {**RECIPE, "target": {"type": "r", "r": 2.5}}, {"sharpeOOS": 1.6})
    st.promote(sid, "paper", v2)
    assert st.get_strategy(sid)["paper_version"] == 2
    r = st.rollback(sid)
    assert r == {"queued": False, "from": 2, "to": 1}
    assert st.get_strategy(sid)["paper_version"] == 1
    assert st.recipe(sid, 1)["target"]["r"] == 2.0
    acts = [x["action"] for x in conn().execute("SELECT action FROM audit_log").fetchall()]
    assert "strategy.rollback" in acts and acts.count("strategy.version") == 2


def test_live_never_changes_mid_trade(paper):
    sid = st.create(RECIPE)
    st.promote(sid, "live", 1)
    v2 = st.add_version(sid, {**RECIPE, "stop": {"type": "atr", "mult": 2}}, "manual")
    conn().execute("INSERT INTO positions (id, broker, strategy_id, market, side, qty, entry, status, opened_at) VALUES ('p','paper',?,'XAU/USD','buy',1,1,'open',0)", (sid,))
    assert st.promote(sid, "live", v2)["queued"] is True
    assert st.get_strategy(sid)["live_version"] == 1
    conn().execute("UPDATE positions SET status='closed' WHERE id='p'")
    assert st.apply_pending(sid)
    assert st.get_strategy(sid)["live_version"] == 2
    assert st.rollback(sid)["to"] == 1


def test_auto_update_goes_to_paper_and_asks(paper):
    sid = st.create(RECIPE, status="paper")
    st.promote(sid, "live", 1)
    assert not st.auto_update(sid, RECIPE, {"sharpeOOS": 1.5}, {"sharpeOOS": 1.4})["accepted"]
    r = st.auto_update(sid, {**RECIPE, "params": {"x": 1}}, {"sharpeOOS": 1.8}, {"sharpeOOS": 1.4})
    assert r["accepted"] and r["asked"] and not r["live"]
    s = st.get_strategy(sid)
    assert s["paper_version"] == r["version"] and s["live_version"] == 1
    assert recent("decision_needed")


def test_signed_pack_installs_into_lab_only():
    import json
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    from nsq.crypto import b64e
    k = Ed25519PrivateKey.generate()
    pub = k.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw).hex()
    raw = json.dumps({"name": "NSKO Gold Pack", "strategies": [RECIPE]}).encode()
    tok = f"NSQPACK1.{b64e(raw)}.{b64e(k.sign(raw))}"
    ids = st.install_pack(tok, public_key_hex=pub)
    assert st.get_strategy(ids[0])["status"] == "lab"
    with pytest.raises(st.StrategyError):
        st.install_pack(tok.replace(tok.split(".")[1][:8], "AAAAAAAA"), public_key_hex=pub)


# ------------------------------------------------------------------ live unlock
def test_live_unlock_needs_everything(paper):
    from nsq.trading.live_unlock import PHRASE, checklist, size_factor, unlock
    cl = checklist(PHRASE, paper, "valid")
    assert not cl["ok"]
    missing = {i["id"] for i in cl["items"] if not i["ok"]}
    assert {"paper_days", "paper_trades", "real_broker"} <= missing
    assert not unlock("i understand", paper, "valid")["unlocked"]
    for i in range(30):
        conn().execute("INSERT INTO journal (ts, pnl, mode) VALUES (?,?,?)", (time.time() - 22 * 86400 + i, 1.0, "paper"))

    class FakeReal:
        name = "alpaca"
        def permissions(self):
            return {"trading": True, "withdrawals": False}
    assert unlock(PHRASE, FakeReal(), "valid")["unlocked"]
    assert size_factor("live") == 0.5, "first 2 weeks of live at 50% size"
    assert size_factor("paper") == 1.0


# ------------------------------------------------------------------ demo + API + bus
def test_demo_source_matches_sim_shapes():
    from nsq.demo import DemoSource
    d = DemoSource()
    for k in range(200):
        d.tick_once(k)
    types = {e["type"] for e in recent(n=5000)}
    for t in ("tick", "orderflow_bubble", "ticker_log", "source_added", "variant_tested", "budget_update", "scan_hit"):
        assert t in types
    assert all(e["payload"].get("demo") is True for e in recent(n=5000)), "every demo number is flagged demo"
    v = recent("variant_tested")[-1]["payload"]
    assert set(v) >= {"id", "recipe", "market", "tf", "sharpeIS", "sharpeOOS", "trades", "win", "rr", "dd", "outcome", "why", "seed"}
    t = recent("tick")[-1]["payload"]
    assert set(t) >= {"market", "price", "bid", "ask"}


def test_health_and_websocket():
    from fastapi.testclient import TestClient
    from nsq import health
    from nsq.app import create_app
    c = TestClient(create_app(start_engine=False))
    h = c.get("/health").json()
    assert {"uptime", "heartbeat", "cpu", "ram"} <= set(h)
    with c.websocket_connect("/ws") as ws:
        first = ws.receive_json()
        assert first["type"] == "engine_health"
        health.beat()
        ev = ws.receive_json()
        assert ev["type"] == "engine_health" and {"ts", "payload"} <= set(ev) and ev["payload"]["round"] >= 1


def test_brokers_catalogue_and_permissions(paper):
    from fastapi.testclient import TestClient
    from nsq.app import create_app
    c = TestClient(create_app(start_engine=False))
    b = {x["name"]: x for x in c.get("/brokers").json()["brokers"]}
    assert b["paper"]["status"] == "ready" and b["cmc"]["status"] == "unsupported"
    assert b["oanda"]["status"] == "coming_soon" and b["oanda"]["reason"]
    p = c.get("/brokers/permissions").json()
    assert p["trading"] is True and p["withdrawals"] is False
