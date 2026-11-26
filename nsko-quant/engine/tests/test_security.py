"""Account (create / login / wrong password / TOTP / PIN / recovery), licences, audit chain, vault, backup, redaction."""
import datetime as dt
import json
import sqlite3

import pyotp
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from nsq import account, licence
from nsq.audit import audit, verify_chain
from nsq.db import conn, db_path


# ------------------------------------------------------------------ account
def test_create_login_wrong_password():
    r = account.create("Ernest@Example.com", "correct horse battery", name="E")
    assert r["recovery_code"] and r["token"]
    assert account.login("ernest@example.com", "correct horse battery")["ok"]
    with pytest.raises(account.AccountError) as e:
        account.login("ernest@example.com", "wrong password!!")
    assert e.value.code == "wrong_password"
    row = conn().execute("SELECT pw_hash FROM account").fetchone()
    assert row["pw_hash"].startswith("$argon2id$")


def test_weak_password_and_duplicate():
    with pytest.raises(account.AccountError):
        account.create("a@b.co", "short")
    account.create("a@b.co", "long enough pw")
    with pytest.raises(account.AccountError) as e:
        account.create("a@b.co", "long enough pw")
    assert e.value.code == "exists"


def test_totp_flow():
    tok = account.create("t@example.com", "a-long-password")["token"]
    s = account.session(tok)
    setup = account.totp_begin(s)
    assert setup["otpauth_uri"].startswith("otpauth://totp/")
    assert not account.totp_confirm(s, "000000")
    assert account.totp_confirm(s, pyotp.TOTP(setup["secret"]).now())
    with pytest.raises(account.AccountError) as e:
        account.login("t@example.com", "a-long-password")
    assert e.value.code == "totp_required"
    with pytest.raises(account.AccountError) as e:
        account.login("t@example.com", "a-long-password", "123456" if pyotp.TOTP(setup["secret"]).now() != "123456" else "654321")
    assert e.value.code == "wrong_totp"
    assert account.login("t@example.com", "a-long-password", pyotp.TOTP(setup["secret"]).now())["totp"]
    raw = conn().execute("SELECT totp_enc FROM account").fetchone()["totp_enc"]
    assert setup["secret"] not in raw, "TOTP secret is encrypted at rest"


def test_pin_and_lockout():
    account.create("p@example.com", "a-long-password", pin="123456")
    assert account.verify_pin("123456")
    for _ in range(5):
        assert not account.verify_pin("000000")
    with pytest.raises(account.AccountError):
        account.verify_pin("123456")


def test_recovery_code_resets_password_and_keeps_data_key():
    r = account.create("r@example.com", "first-password-1")
    dek1 = account.session(r["token"]).dek
    out = account.recover(r["recovery_code"].lower(), "second-password-2")
    assert out["recovery_code"] != r["recovery_code"]
    with pytest.raises(account.AccountError):
        account.login("r@example.com", "first-password-1")
    tok = account.login("r@example.com", "second-password-2")["token"]
    assert account.session(tok).dek == dek1, "same data key: encrypted data survives the reset"
    with pytest.raises(account.AccountError):
        account.recover(r["recovery_code"], "third-password-3")   # old code no longer works


def test_account_endpoints():
    from fastapi.testclient import TestClient
    from nsq.app import create_app
    c = TestClient(create_app(start_engine=False))
    h = {"X-NSQ-Client": "test"}
    r = c.post("/account/create", json={"email": "x@example.com", "password": "a-long-password"}, headers=h)
    assert r.status_code == 200 and r.json()["recovery_code"]
    assert c.post("/account/login", json={"email": "x@example.com", "password": "nope-nope-nope"}, headers=h).status_code == 401
    assert c.post("/account/login", json={"email": "x@example.com", "password": "a-long-password"}, headers=h).status_code == 200


# ------------------------------------------------------------------ licence
@pytest.fixture
def keypair():
    k = Ed25519PrivateKey.generate()
    pub = k.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw).hex()
    return k, pub


def _token(k, **over):
    import importlib.util
    import pathlib
    p = pathlib.Path(__file__).resolve().parents[2] / "tools" / "make-licence" / "make_licence.py"
    spec = importlib.util.spec_from_file_location("make_licence", p)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    a = {"name": "Jane", "email": "jane@example.com", "expiry": "2027-12-31", "tier": "Pro"} | over
    return m.make_token(k, a["name"], a["email"], a["expiry"], a["tier"])


def test_licence_valid(keypair):
    k, pub = keypair
    r = licence.check(_token(k), public_key_hex=pub, today=dt.date(2026, 11, 26))
    assert r["status"] == "valid" and r["licence"]["tier"] == "Pro"


def test_licence_expired(keypair):
    k, pub = keypair
    r = licence.check(_token(k, expiry="2026-01-01"), public_key_hex=pub, today=dt.date(2026, 11, 26))
    assert r["status"] == "expired"


def test_licence_invalid(keypair):
    k, pub = keypair
    t = _token(k)
    head, p64, sig = t.split(".")
    payload = json.loads(licence.b64d(p64))
    payload["tier"] = "Pro"
    payload["expiry"] = "2099-12-31"
    forged = ".".join([head, licence.b64d.__globals__["b64e"](json.dumps(payload).encode()), sig])
    assert licence.check(forged, public_key_hex=pub)["status"] == "invalid"
    other = Ed25519PrivateKey.generate()
    assert licence.check(_token(other), public_key_hex=pub)["status"] == "invalid"
    assert licence.check("garbage", public_key_hex=pub)["status"] == "invalid"


def test_engine_has_embedded_public_key_only():
    from nsq.licence_key import PUBLIC_KEY_HEX
    assert len(PUBLIC_KEY_HEX) == 64
    import pathlib
    import nsq
    for p in pathlib.Path(nsq.__file__).parent.rglob("*"):
        if p.is_file() and p.suffix in (".py", ".pem", ".key"):
            assert "PRIVATE KEY" not in p.read_text(errors="ignore") or p.name == "test_security.py"


# ------------------------------------------------------------------ audit chain
def test_audit_chain_detects_tampering():
    for i in range(5):
        audit("t", "act", {"i": i})
    assert verify_chain()["ok"]
    c = conn()
    with pytest.raises(sqlite3.DatabaseError):
        c.execute("UPDATE audit_log SET detail='{}' WHERE id=2")
    with pytest.raises(sqlite3.DatabaseError):
        c.execute("DELETE FROM audit_log WHERE id=2")
    raw = sqlite3.connect(db_path())                     # an attacker drops the triggers and edits a row
    raw.execute("DROP TRIGGER audit_log_no_update")
    raw.execute("""UPDATE audit_log SET detail='{"i": 99}' WHERE id=3""")
    raw.commit()
    raw.close()
    r = verify_chain()
    assert not r["ok"] and r["bad_id"] == 3


def test_audit_redacts_secrets():
    audit("t", "broker.connect", {"api_key": "SUPERSECRET123", "market": "XAU/USD"})
    row = conn().execute("SELECT detail FROM audit_log ORDER BY id DESC LIMIT 1").fetchone()
    assert "SUPERSECRET123" not in row["detail"] and "XAU/USD" in row["detail"]


def test_log_lines_are_redacted(capsys):
    import logging
    from nsq.log import JsonFormatter
    rec = logging.LogRecord("nsq.x", logging.INFO, "", 0, "connect key=abcd1234SECRET token: zzz Bearer qqq", None, None)
    line = JsonFormatter().format(rec)
    for s in ("abcd1234SECRET", "zzz", "qqq"):
        assert s not in line


# ------------------------------------------------------------------ vault + backup
def test_vault_file_fallback_is_encrypted(fresh):
    from nsq import vault
    tok = account.create("v@example.com", "a-long-password")["token"]
    assert vault.backend() == "encrypted-file"
    vault.put("kraken.secret", "MY-BROKER-SECRET")
    assert vault.get("kraken.secret") == "MY-BROKER-SECRET"
    assert b"MY-BROKER-SECRET" not in (fresh / "vault.bin").read_bytes()
    account.logout(tok)
    assert vault.get("kraken.secret") is None, "locked without a signed-in user"


def test_backup_roundtrip_never_contains_broker_keys(fresh):
    from nsq import vault
    from nsq.backup import export, restore
    from nsq.settings import get, set as sset
    account.create("b@example.com", "a-long-password")
    vault.put("alpaca.secret", "ALPACA-SECRET-VALUE")
    sset("risk.per_trade_pct", 0.5)
    blob = export("backup-pass-123")
    assert b"ALPACA-SECRET-VALUE" not in blob and b"risk.per_trade_pct" not in blob
    sset("risk.per_trade_pct", 1.0)
    with pytest.raises(ValueError):
        restore(blob, "wrong")
    out = restore(blob, "backup-pass-123")
    assert out["ok"] and get("risk.per_trade_pct") == 0.5
    import json as _j
    from nsq.crypto import open_with_passphrase
    plain = open_with_passphrase("backup-pass-123", blob, b"nsq:backup").decode()
    assert "ALPACA-SECRET-VALUE" not in plain
    assert "account" in _j.loads(plain)["tables"]
