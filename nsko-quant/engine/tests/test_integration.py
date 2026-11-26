"""Stage 4 integration: the endpoints and shapes the desktop UI uses, the tray's shared secret, CORS, the
WebSocket token, session-protected stage-3 POSTs, JARVIS chat, the dev demo trade and the CLI flags."""
import base64
import os
import stat
import subprocess
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from nsq import account, localauth
from nsq.settings import get, set as sset

H = {"X-NSQ-Client": "test"}


@pytest.fixture
def client(monkeypatch):
    monkeypatch.delenv("NSQ_DEV", raising=False)
    localauth._reset_for_tests()
    from nsq.app import create_app
    return TestClient(create_app(start_engine=False))


@pytest.fixture
def auth(client):
    tok = client.post("/account/create", json={"email": "e@example.com", "password": "a-long-password", "name": "E"},
                      headers=H).json()["token"]
    return {**H, "Authorization": f"Bearer {tok}"}


# ------------------------------------------------------------------ CORS + CSRF guard
def test_cors_allows_desktop_origins_only(client):
    for origin in ("tauri://localhost", "http://tauri.localhost", "http://localhost:5173", "http://localhost:4173"):
        r = client.options("/kill", headers={"Origin": origin, "Access-Control-Request-Method": "POST",
                                             "Access-Control-Request-Headers": "x-nsq-client,content-type"})
        assert r.status_code == 200 and r.headers["access-control-allow-origin"] == origin
    r = client.options("/kill", headers={"Origin": "https://evil.example", "Access-Control-Request-Method": "POST"})
    assert "access-control-allow-origin" not in r.headers
    # a refused POST still carries CORS headers, so the desk can read the reason
    r = client.post("/kill", headers={"Origin": "tauri://localhost"})
    assert r.status_code == 403 and r.headers.get("access-control-allow-origin") == "tauri://localhost"


# ------------------------------------------------------------------ tray: shared secret, pause, shutdown, kill
def test_shell_token_file_is_private_and_unlocks_pause(client, paper):
    with client:   # runs the lifespan: the engine writes the token file at start
        p = localauth.path()
        assert p.exists() and len(p.read_text()) >= 40
        if os.name == "posix":
            assert stat.S_IMODE(p.stat().st_mode) == 0o600
        assert client.post("/trading/pause", json={"paused": True}, headers=H).status_code == 401
        assert client.post("/trading/pause", json={"paused": True}, headers={**H, "X-NSQ-Shell": "wrong"}).status_code == 401
        r = client.post("/trading/pause", json={"paused": True}, headers={**H, "X-NSQ-Shell": p.read_text()})
        assert r.status_code == 200 and r.json()["trading_paused"] is True
        h = client.get("/health").json()
        assert h["paused"] is True and h["killed"] is False
        client.post("/trading/pause", json={"paused": False}, headers={**H, "X-NSQ-Shell": p.read_text()})
        assert client.get("/health").json()["paused"] is False


def test_pause_blocks_new_trades_only(paper):
    from nsq.trading import strategies as st
    from nsq.trading.flow import TradeFlow
    from test_flow import NOW, RECIPE, last_bar_signal
    from conftest import trend_candles
    st.create(RECIPE, status="paper")
    sset("trading.paused", True)
    r = TradeFlow(paper, signals_fn=last_bar_signal).run(st.approved()[0], now=NOW, df=trend_candles())
    assert r["result"] == "skipped" and "paused" in r["why"]


def test_engine_shutdown_needs_session_or_shell(client, auth, monkeypatch):
    import nsq.app as appmod
    called = []
    monkeypatch.setattr(appmod, "_stop_process", lambda: called.append(1))
    assert client.post("/engine/shutdown", headers=H).status_code == 401
    assert client.post("/engine/shutdown", headers={**H, "X-NSQ-Shell": localauth.current()}).json()["stopping"]
    assert client.post("/engine/shutdown", headers=auth).status_code == 200
    import time
    time.sleep(0.6)
    assert len(called) == 2


def test_kill_always_works_and_release_needs_login(client, auth, paper):
    assert client.post("/kill", json={"reason": "tray", "source": "tray"}, headers=H).json()["locked"] is True
    assert client.get("/health").json()["killed"] is True
    assert client.post("/trading/enable", headers=H).status_code == 401
    assert client.post("/trading/enable", headers=auth).json()["locked"] is False
    assert client.get("/health").json()["killed"] is False


# ------------------------------------------------------------------ session-protected stage-3 POSTs
def test_stage3_posts_need_a_session(client, auth):
    for path in ("/lab/seed", "/research/round", "/godseye/scan", "/data/news/poll", "/kb/measure"):
        assert client.post(path, json={}, headers=H).status_code == 401, path
    assert client.post("/lab/seed", headers=auth).status_code == 200
    assert client.get("/lab/recipes").status_code == 200      # reading stays open on localhost


# ------------------------------------------------------------------ account / licence shapes the desk uses
def test_login_without_email_and_licence_check_by_key(client, auth):
    r = client.post("/account/login", json={"password": "a-long-password"}, headers=H)
    assert r.status_code == 200 and r.json()["token"]
    r = client.post("/account/login", json={"password": "wrong-password!"}, headers=H)
    assert r.status_code == 401 and r.json()["detail"]["code"] == "wrong_password"
    assert client.get("/licence/check", params={"key": "garbage"}).json()["status"] == "invalid"
    assert get("licence.key", "") in ("", None), "checking a key never saves it"


def test_create_with_licence(client, monkeypatch):
    r = client.post("/account/create", json={"email": "l@example.com", "password": "a-long-password", "licence_key": "NSQ1.x.y"},
                    headers=H)
    assert r.status_code == 400 and r.json()["detail"]["code"] == "licence_invalid"
    assert not account.exists(), "no account is made with a bad licence"
    import nsq.app as appmod
    monkeypatch.setattr(appmod.licence, "check", lambda k: {"status": "valid", "reason": "ok", "licence": {"tier": "Pro"}})
    r = client.post("/account/create", json={"email": "l@example.com", "password": "a-long-password", "licence_key": "NSQ1.good"},
                    headers=H)
    assert r.status_code == 200 and r.json()["licence"]["tier"] == "Pro" and get("licence.key") == "NSQ1.good"


def test_totp_begin_shape(client, auth):
    r = client.post("/account/totp/begin", headers=auth).json()
    assert r["secret"] and r["otpauth_uri"].startswith("otpauth://")


# ------------------------------------------------------------------ settings
def test_settings_batch_is_all_or_nothing(client, auth):
    r = client.post("/settings", json={"values": {"risk.per_trade_pct": 0.5, "trade_mode": "manual"}}, headers=auth)
    assert r.status_code == 200 and r.json()["saved"] == ["risk.per_trade_pct", "trade_mode"]
    assert get("risk.per_trade_pct") == 0.5 and get("trade_mode") == "manual"
    r = client.post("/settings", json={"values": {"risk.per_trade_pct": 2.0, "trading.locked": False}}, headers=auth)
    assert r.status_code == 400 and get("risk.per_trade_pct") == 0.5, "a protected key refuses the whole batch"
    assert client.post("/settings", json={"key": "risk.daily_loss_pct", "value": 2.5}, headers=auth).status_code == 200
    assert client.post("/settings", json={"values": {"x": 1}}, headers=H).status_code == 401
    s = client.get("/settings").json()
    assert s["risk.daily_loss_pct"] == 2.5 and "licence.key" not in s


def test_live_start_size_setting():
    from nsq.trading import live_unlock
    sset("live.unlocked_at", 1.0)
    sset("live.start_size_pct", 25)
    assert live_unlock.size_factor("live", now=2.0) == 0.25
    sset("live.start_size_pct", 500)
    assert live_unlock.size_factor("live", now=2.0) == 1.0, "clamped to 100 %"


# ------------------------------------------------------------------ backup as JSON for the desk
def test_backup_export_json_round_trip(client, auth):
    sset("risk.per_trade_pct", 0.7)
    r = client.post("/backup/export", json={"passphrase": "correct horse", "format": "json"}, headers=auth).json()
    assert r["filename"].endswith(".nsko") and base64.b64decode(r["data_b64"])
    sset("risk.per_trade_pct", 1.0)
    out = client.post("/backup/restore", json={"passphrase": "correct horse", "data_b64": r["data_b64"]}, headers=auth).json()
    assert out["ok"] and get("risk.per_trade_pct") == 0.7
    raw = client.post("/backup/export", json={"passphrase": "correct horse"}, headers=auth)
    assert raw.headers["content-type"] == "application/octet-stream"


# ------------------------------------------------------------------ strategies: versions, rollback to a version, edit
def test_strategy_versions_rollback_to_and_edit(client, auth):
    from nsq.trading import strategies as st
    rec = {"id": "s1", "name": "S1", "market": "XAU/USD", "timeframe": "15m", "entry": {"type": "ema_cross"}, "params": {"fast": 20}}
    st.create(rec, status="paper")
    for f in (18, 16):
        st.add_version("s1", {**rec, "params": {"fast": f}}, "lab", {"sharpeOOS": 1.5}, f"fast {f}")
    st.promote("s1", "paper", 3)
    row = client.get("/strategies", params={"include": "versions"}).json()["strategies"][0]
    assert [v["version"] for v in row["versions"]] == [1, 2, 3] and row["active_version"] == 3
    r = client.post("/strategies/s1/rollback", json={"version": 1}, headers=auth).json()
    assert r == {"queued": False, "from": 3, "to": 1}
    assert client.post("/strategies/s1/rollback", json={"version": 1}, headers=auth).status_code == 400, "already active"
    assert client.post("/strategies/s1/rollback", json={"version": 9}, headers=auth).status_code == 400
    assert client.post("/strategies/s1/rollback", headers=auth).status_code == 400, "nothing before v1"
    r = client.post("/strategies/s1/versions", json={"rules": {**rec, "params": {"fast": 12}}, "note": "Edit: fast 12"}, headers=auth)
    assert r.json() == {"version": 4, "where": "lab"}
    assert st.get_strategy("s1")["paper_version"] == 1, "an edit runs nowhere until promoted"
    assert client.post("/strategies/nope/versions", json={"rules": {}}, headers=auth).status_code == 404


def test_auto_update_modes():
    from nsq.trading import strategies as st
    from nsq.bus import recent
    rec = {"id": "s2", "name": "S2", "market": "XAU/USD", "timeframe": "15m", "entry": {"type": "ema_cross"}, "params": {}}
    st.create(rec, status="paper")
    sset("updates.mode", "manual")
    assert st.auto_update("s2", rec, {"sharpeOOS": 3}, {"sharpeOOS": 1})["accepted"] is False
    sset("updates.mode", "ask")
    r = st.auto_update("s2", rec, {"sharpeOOS": 3}, {"sharpeOOS": 1})
    assert r["asked"] and r["paper"] is False and recent("decision_needed")[-1]["payload"]["tag"] == "TO PAPER"


# ------------------------------------------------------------------ withdraw helper steps, checklist
def test_withdraw_steps(client, auth, paper):
    from nsq.brokers.base import value_per_point  # noqa: F401  (paper broker import side effects)
    paper.place_bracket("XAU/USD", "buy", 0.1, 2640.0, 2670.0, "w-1")
    w = client.get("/withdraw/helper").json()
    assert w["open_positions"] == 1 and w["positions"][0]["market"] == "XAU/USD" and w["trading_paused"] is False
    assert client.post("/withdraw/helper", json={"action": "close_positions"}, headers=auth).status_code == 400, "pause first"
    assert client.post("/withdraw/helper", json={"action": "pause"}, headers=auth).json()["trading_paused"] is True
    r = client.post("/withdraw/helper", json={"action": "close_positions"}, headers=auth).json()
    assert r["closed"] == 1 and r["positions"] == []
    assert client.post("/withdraw/helper", json={"action": "rescale"}, headers=auth).json()["new_equity"] > 0
    assert client.post("/withdraw/helper", json={"action": "resume"}, headers=auth).json()["trading_paused"] is False
    assert client.post("/withdraw/helper", json={"action": "send_money"}, headers=auth).status_code == 400
    assert client.post("/withdraw/helper", json={"action": "pause"}, headers=H).status_code == 401


def test_live_checklist_shape(client):
    c = client.get("/live/checklist").json()
    assert c["phrase"] == "I understand I can lose money" and {"trades", "days", "r", "win"} <= set(c["paper"])
    assert c["unlocked"] is False and any(i["id"] == "paper_days" for i in c["items"])


# ------------------------------------------------------------------ brokers: the desk's connect shape
def test_broker_connect_desk_shape(client, auth):
    lst = client.get("/brokers").json()
    assert lst["active"] == "paper" and all("key_stored" in b for b in lst["brokers"])
    assert client.post("/brokers/paper/connect", json={"environment": "demo"}, headers=auth).json()["broker"] == "paper"
    r = client.post("/brokers/oanda/connect", json={"environment": "demo"}, headers=auth)
    assert r.status_code == 400 and "OANDA" in r.json()["detail"]
    assert "Paste the API key" in client.post("/brokers/kraken/connect", json={}, headers=auth).json()["detail"]
    r = client.post("/brokers/kraken/connect", json={"keychain_service": "other.app", "keychain_account": "broker:kraken:demo"},
                    headers=auth)
    assert r.status_code == 400 and "keychain_service" in r.json()["detail"]
    assert client.post("/brokers/paper/connect", json={}, headers=H).status_code == 401


def test_broker_connect_puts_browser_key_in_vault(client, auth, monkeypatch):
    from nsq import vault
    import nsq.app as appmod

    class Fake:
        name = "kraken"
        def connect(self): return True
        def permissions(self): return {"trading": True, "withdrawals": None}
    monkeypatch.setattr(appmod, "build", lambda name, live=False: Fake())
    monkeypatch.setattr("nsq.recovery.reconcile", lambda b: {"ok": True})
    r = client.post("/brokers/kraken/connect", json={"environment": "demo", "api_key": "K-123", "api_secret": "S-456"}, headers=auth)
    assert r.status_code == 200 and r.json()["broker"] == "kraken"
    assert vault.get("kraken.key") == "K-123" and vault.get("kraken.secret") == "S-456"
    assert "K-123" not in str(client.get("/settings").json()) and "K-123" not in str(client.get("/vault").json())
    from nsq.brokers import set_active
    set_active(None)


# ------------------------------------------------------------------ JARVIS
def test_jarvis_chat_honest_without_local_model(client, auth, paper, monkeypatch):
    from nsq.research import llm
    monkeypatch.setattr(llm, "available", lambda recheck_s=120: False)
    r = client.post("/jarvis/chat", json={"message": "How is gold?"}, headers=auth).json()
    assert r["local_model"] is False and "not installed" in r["reply"] and "Open positions: 0" in r["reply"]
    assert client.post("/jarvis/chat", json={"message": "hi"}, headers=H).status_code == 401
    assert client.post("/jarvis/chat", json={"message": "  "}, headers=auth).status_code == 400


def test_jarvis_chat_uses_ollama_when_up(client, auth, monkeypatch):
    from nsq.research import llm
    seen = {}
    monkeypatch.setattr(llm, "available", lambda recheck_s=120: True)
    monkeypatch.setattr(llm, "generate", lambda prompt, as_json=True, timeout=120: seen.setdefault("p", prompt) and "Gold is flat.")
    r = client.post("/jarvis/chat", json={"message": "How is gold?", "history": [{"me": True, "t": "hello"}]}, headers=auth).json()
    assert r["local_model"] is True and r["reply"] == "Gold is flat."
    assert "FACTS" in seen["p"] and "User: hello" in seen["p"] and "How is gold?" in seen["p"]


# ------------------------------------------------------------------ dev demo trade (NSQ_DEV=1 only)
def test_dev_router_only_with_nsq_dev(client, auth, monkeypatch):
    assert client.post("/dev/run-demo-trade", headers=auth).status_code == 404
    monkeypatch.setenv("NSQ_DEV", "1")
    from nsq.app import create_app
    c = TestClient(create_app(start_engine=False))
    assert c.post("/dev/run-demo-trade", headers=H).status_code == 401, "needs a session even in dev"


def test_dev_demo_trade_runs_the_real_flow(paper, monkeypatch):
    monkeypatch.setenv("NSQ_DEV", "1")
    from nsq import devtools
    from nsq.bus import recent
    from nsq.db import conn
    sset("forecast.paths", 400)
    sset("timemachine.replays", 2000)
    devtools._state["running"] = True
    devtools._run(devtools.DemoTrade(walk_to_exit=True, step_s=0))
    last = devtools._state["last"]
    assert last["result"] == "executed" and last.get("exit"), last
    for ev in ("scan_hit", "news_hit", "forecast_done", "entry_state", "timemachine_done", "size_calc", "risk_check",
               "order_sent", "order_filled", "position_update", "exit_done"):
        assert recent(ev), ev
    assert conn().execute("SELECT COUNT(*) n FROM journal").fetchone()["n"] == 1
    assert conn().execute("SELECT COUNT(*) n FROM strategy_versions WHERE strategy_id=?", (devtools.DEV_SID,)).fetchone()["n"] == 2
    assert recent("scan_hit")[-1]["payload"]["synthetic"] is True, "synthetic candles are flagged"


# ------------------------------------------------------------------ CLI (PyInstaller entry / Tauri sidecar flags)
def test_cli_version_and_localhost_only():
    eng = Path(__file__).resolve().parents[1]
    r = subprocess.run([sys.executable, "-m", "nsq", "--version"], cwd=eng, capture_output=True, text=True, timeout=60)
    assert r.returncode == 0 and r.stdout.startswith("NSKO QUANT engine ")
    env = {k: v for k, v in os.environ.items() if k != "NSQ_ALLOW_NON_LOCAL"}
    r = subprocess.run([sys.executable, "-m", "nsq", "--host", "0.0.0.0", "--port", "1"], cwd=eng, capture_output=True,
                       text=True, timeout=60, env=env)
    assert r.returncode == 2 and "localhost-only" in r.stderr
    r = subprocess.run([sys.executable, str(eng.parent / "deploy" / "pyinstaller" / "entry.py"), "--version"], cwd=eng,
                       capture_output=True, text=True, timeout=60, env={**env, "PYTHONPATH": str(eng)})
    assert r.returncode == 0 and "NSKO QUANT engine" in r.stdout


# ------------------------------------------------------------------ God's Eye risk flags in the risk gate
def _flag(asset, action):
    from nsq.godseye import impact
    from nsq.db import conn
    impact.ensure()
    import time
    conn().execute("INSERT INTO godseye_risk_flags (impact_id, asset, action, expires_at, created_at) VALUES (?,?,?,?,?)",
                   (f"test_rule:{action}:x", asset, action, int(time.time() * 1000) + 3_600_000, int(time.time() * 1000)))


def _run_trade(paper):
    from nsq.trading import strategies as st
    from nsq.trading.flow import TradeFlow
    from test_flow import NOW, RECIPE, last_bar_signal
    from conftest import trend_candles
    sset("forecast.paths", 400)
    sset("timemachine.replays", 2000)
    df = trend_candles()
    paper.set_price("XAU/USD", float(df["close"].iloc[-1]), ts=NOW.timestamp())
    st.create(RECIPE, status="paper")
    return TradeFlow(paper, signals_fn=last_bar_signal).run(st.approved()[0], now=NOW, df=df)


def test_godseye_pause_new_blocks_only_when_apply(paper):
    from nsq.trading import risk
    _flag("XAU/USD", "pause_new")
    assert risk.godseye_flags("XAU/USD")["applied"] is False, "suggest mode: flags are ignored"
    sset("godseye.risk_actions", "apply")
    g = risk.godseye_flags("XAU/USD")
    assert g["pause"] and not risk.godseye_flags("BTC/USD")["pause"], "only the flagged market"
    r = _run_trade(paper)
    assert r["result"] == "skipped" and r["step"] == "risk" and "God's Eye paused new entries" in r["why"]
    assert paper.positions() == []


def test_godseye_cut_size_halves_the_trade(paper):
    base = _run_trade(paper)
    assert base["result"] == "executed"
    q_full = base["size"]["qty"]
    for p in paper.positions():
        paper.close(p.id)
    from nsq.db import conn
    conn().execute("DELETE FROM strategies"); conn().execute("DELETE FROM strategy_versions")
    sset("godseye.risk_actions", "apply")
    _flag("XAUUSD", "cut_size")            # asset names are matched without punctuation
    r = _run_trade(paper)
    assert r["result"] == "executed" and r["size"]["godseye_cut"] == 0.5
    assert r["size"]["qty"] <= q_full / 2 + 1e-9
    assert any(c["rule"] == "godseye_flags" and c["passed"] for c in r["risk"]["checks"])


# ------------------------------------------------------------------ alerts set-up: telegram pairing, test alert
def test_telegram_pairing_flow(client, auth):
    from nsq import notify, vault
    assert client.post("/telegram/pair/begin", headers=auth).status_code == 400, "token first"
    assert client.post("/vault/telegram.bot_token", json={"value": "123:ABC"}, headers=auth).json()["ok"]
    assert "123:ABC" not in str(client.get("/vault").json()) and "telegram.bot_token" in client.get("/vault").json()["names"]
    code = client.post("/telegram/pair/begin", headers=auth).json()["code"]
    assert "notify.telegram_pair" not in client.get("/settings").json(), "the code hash never leaves the engine"
    upd = lambda chat, text: {"message": {"chat": {"id": chat}, "text": text}}
    assert notify.handle_telegram_update(upd(42, "/pair 000000" if code != "000000" else "/pair 111111")) == "refused"
    assert notify.handle_telegram_update(upd(99, "/kill")) == "refused", "not paired yet"
    assert notify.handle_telegram_update(upd(42, f"/pair {code}")) == "paired"
    assert get("notify.telegram_chat_id") == "42"
    assert notify.handle_telegram_update(upd(7, f"/pair {code}")) == "refused", "a code works once"
    assert vault.get("telegram.bot_token") == "123:ABC"


def test_notify_test_endpoint(client, auth, monkeypatch):
    from nsq import notify
    monkeypatch.setattr(notify, "_ntfy", lambda t, b, l: "ok")
    monkeypatch.setattr(notify, "_telegram", lambda t, b: "skipped")
    sset("notify.ntfy_topic", "my-topic")
    r = client.post("/notify/test", headers=auth).json()
    assert "'ntfy': 'ok'" in r["delivered"] and r["ntfy_topic_set"] is True and r["telegram_paired"] is False
    sset("notify.ntfy_enabled", False)
    r = client.post("/notify/test", headers=auth).json()
    assert "off in settings" in r["delivered"]
    assert client.post("/notify/test", headers=H).status_code == 401
