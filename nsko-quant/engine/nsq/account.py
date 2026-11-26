"""In-app account (section 4.2): one local account per desk.

- Password hashed with Argon2id (argon2-cffi PasswordHasher).
- A random 256-bit data key (DEK) encrypts sensitive local data (TOTP secret, vault fallback file).
  The DEK is stored twice, wrapped by a key derived (Argon2id) from the password and from the
  recovery code. Forgetting the password: the recovery code unwraps the DEK and re-wraps it.
- Optional 6-digit PIN (quick unlock, Argon2id hash, 5 tries then a 5-minute lockout).
  The PIN never unwraps the DEK: 6 digits are too few to protect data on their own.
- Optional TOTP 2FA (pyotp), secret sealed with the DEK.
- Sessions are random bearer tokens held in memory only.
"""
from __future__ import annotations

import os
import re
import secrets
import threading
import time
from dataclasses import dataclass, field

import pyotp
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

from . import crypto
from .audit import audit
from .db import conn

_ph = PasswordHasher()  # argon2id defaults
if os.environ.get("NSQ_FAST_KDF") == "1":  # tests only
    _ph = PasswordHasher(time_cost=1, memory_cost=8 * 1024, parallelism=1)

AAD_DEK, AAD_TOTP = b"nsq:dek", b"nsq:totp"
SESSION_TTL_S = 12 * 3600


class AccountError(Exception):
    def __init__(self, code: str, msg: str):
        super().__init__(msg)
        self.code, self.msg = code, msg


@dataclass
class Session:
    token: str
    email: str
    dek: bytes = field(repr=False)
    created: float = field(default_factory=time.time)


_sessions: dict[str, Session] = {}
_lock = threading.Lock()
_pin_fail = {"n": 0, "until": 0.0}
_login_fail = {"n": 0, "until": 0.0}


def _verify(h: str | None, secret: str) -> bool:
    if not h:
        return False
    try:
        return _ph.verify(h, secret)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def _new_recovery_code() -> str:
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    raw = "".join(secrets.choice(alphabet) for _ in range(24))
    return "-".join(raw[i:i + 4] for i in range(0, 24, 4))


def _norm_recovery(code: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", code.upper())


def _row() -> dict | None:
    return conn().execute("SELECT * FROM account WHERE id=1").fetchone()


def exists() -> bool:
    return _row() is not None


def _check_password_strength(pw: str) -> None:
    if len(pw) < 10:
        raise AccountError("weak_password", "Use at least 10 characters for your password.")


def create(email: str, password: str, name: str = "", pin: str | None = None) -> dict:
    """Create the desk account. Returns the recovery code ONCE (it is never stored in clear)."""
    if exists():
        raise AccountError("exists", "An account already exists on this desk.")
    if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email or ""):
        raise AccountError("bad_email", "That email address does not look right.")
    _check_password_strength(password)
    if pin is not None and not re.fullmatch(r"\d{6}", pin):
        raise AccountError("bad_pin", "The PIN must be exactly 6 digits.")
    salt = os.urandom(16)
    dek = os.urandom(32)
    recovery = _new_recovery_code()
    kek_pw = crypto.derive_key(password, salt)
    kek_rc = crypto.derive_key(_norm_recovery(recovery), salt + b"rc")
    conn().execute(
        "INSERT INTO account (id, name, email, pw_hash, pin_hash, totp_enc, recovery_hash, kdf_salt, dek_by_pw, dek_by_recovery, created_at)"
        " VALUES (1,?,?,?,?,?,?,?,?,?,?)",
        (name, email.lower(), _ph.hash(password), _ph.hash(pin) if pin else None, None,
         _ph.hash(_norm_recovery(recovery)), crypto.b64e(salt),
         crypto.seal(kek_pw, dek, AAD_DEK), crypto.seal(kek_rc, dek, AAD_DEK), time.time()),
    )
    audit("user", "account.create", {"email": email.lower(), "pin": bool(pin)})
    sess = _open_session(email.lower(), dek)
    return {"ok": True, "email": email.lower(), "recovery_code": recovery, "token": sess.token,
            "note": "Write the recovery code down and keep it safe. It is shown only once."}


def _open_session(email: str, dek: bytes) -> Session:
    s = Session(token=secrets.token_urlsafe(32), email=email, dek=dek)
    with _lock:
        _sessions[s.token] = s
    return s


def login(email: str, password: str, totp: str | None = None) -> dict:
    now = time.time()
    if _login_fail["until"] > now:
        raise AccountError("locked", f"Too many tries. Wait {int(_login_fail['until'] - now)} s.")
    r = _row()
    if not r or r["email"] != (email or "").lower() or not _verify(r["pw_hash"], password):
        _login_fail["n"] += 1
        if _login_fail["n"] >= 5:
            _login_fail.update(n=0, until=now + 60)
        audit("user", "account.login_failed", {"email": (email or "").lower(), "why": "wrong_password"})
        raise AccountError("wrong_password", "Email or password is not right.")
    dek = crypto.open_(crypto.derive_key(password, crypto.b64d(r["kdf_salt"])), r["dek_by_pw"], AAD_DEK)
    if r["totp_enc"]:
        secret = crypto.open_(dek, r["totp_enc"], AAD_TOTP).decode()
        if not totp:
            raise AccountError("totp_required", "Enter the 6-digit code from your authenticator app.")
        if not pyotp.TOTP(secret).verify(str(totp), valid_window=1):
            audit("user", "account.login_failed", {"email": r["email"], "why": "wrong_totp"})
            raise AccountError("wrong_totp", "That code is not right. Check your authenticator app.")
    _login_fail.update(n=0, until=0.0)
    sess = _open_session(r["email"], dek)
    audit("user", "account.login", {"email": r["email"]})
    return {"ok": True, "token": sess.token, "email": r["email"], "totp": bool(r["totp_enc"]), "pin": bool(r["pin_hash"])}


def session(token: str | None) -> Session | None:
    if not token:
        return None
    with _lock:
        s = _sessions.get(token)
        if s and time.time() - s.created > SESSION_TTL_S:
            _sessions.pop(token, None)
            return None
        return s


def any_session() -> Session | None:
    """The engine itself needs the DEK for the vault fallback file while a user is signed in."""
    with _lock:
        return next(iter(_sessions.values()), None)


def logout(token: str) -> None:
    with _lock:
        _sessions.pop(token, None)


def verify_pin(pin: str) -> bool:
    now = time.time()
    if _pin_fail["until"] > now:
        raise AccountError("locked", "Too many wrong PINs. Use your password, or wait 5 minutes.")
    r = _row()
    ok = bool(r and _verify(r["pin_hash"], pin))
    if not ok:
        _pin_fail["n"] += 1
        if _pin_fail["n"] >= 5:
            _pin_fail.update(n=0, until=now + 300)
    else:
        _pin_fail.update(n=0, until=0.0)
    return ok


def set_pin(sess: Session, pin: str | None) -> None:
    if pin is not None and not re.fullmatch(r"\d{6}", pin):
        raise AccountError("bad_pin", "The PIN must be exactly 6 digits.")
    conn().execute("UPDATE account SET pin_hash=? WHERE id=1", (_ph.hash(pin) if pin else None,))
    audit("user", "account.pin", {"enabled": bool(pin)})


def totp_begin(sess: Session) -> dict:
    """Start 2FA set-up: returns the secret and otpauth URI for the QR code. Confirm with totp_confirm."""
    secret = pyotp.random_base32()
    sess.__dict__["_pending_totp"] = secret
    uri = pyotp.TOTP(secret).provisioning_uri(name=sess.email, issuer_name="NSKO QUANT")
    return {"secret": secret, "otpauth_uri": uri}


def totp_confirm(sess: Session, code: str) -> bool:
    secret = sess.__dict__.get("_pending_totp")
    if not secret or not pyotp.TOTP(secret).verify(str(code), valid_window=1):
        return False
    conn().execute("UPDATE account SET totp_enc=? WHERE id=1", (crypto.seal(sess.dek, secret.encode(), AAD_TOTP),))
    sess.__dict__.pop("_pending_totp", None)
    audit("user", "account.totp", {"enabled": True})
    return True


def totp_disable(sess: Session) -> None:
    conn().execute("UPDATE account SET totp_enc=NULL WHERE id=1")
    audit("user", "account.totp", {"enabled": False})


def recover(recovery_code: str, new_password: str) -> dict:
    """Forgotten password: the recovery code re-wraps the data key under a new password.
    A fresh recovery code is issued (the old one stops working). TOTP stays as it was."""
    r = _row()
    rc = _norm_recovery(recovery_code or "")
    if not r or not _verify(r["recovery_hash"], rc):
        audit("user", "account.recover_failed", {})
        raise AccountError("wrong_recovery", "That recovery code is not right.")
    _check_password_strength(new_password)
    salt = crypto.b64d(r["kdf_salt"])
    dek = crypto.open_(crypto.derive_key(rc, salt + b"rc"), r["dek_by_recovery"], AAD_DEK)
    new_rc = _new_recovery_code()
    conn().execute(
        "UPDATE account SET pw_hash=?, recovery_hash=?, dek_by_pw=?, dek_by_recovery=? WHERE id=1",
        (_ph.hash(new_password), _ph.hash(_norm_recovery(new_rc)),
         crypto.seal(crypto.derive_key(new_password, salt), dek, AAD_DEK),
         crypto.seal(crypto.derive_key(_norm_recovery(new_rc), salt + b"rc"), dek, AAD_DEK)),
    )
    with _lock:
        _sessions.clear()
    audit("user", "account.recover", {"email": r["email"]})
    return {"ok": True, "recovery_code": new_rc, "note": "Your new recovery code. The old one no longer works."}


def change_password(sess: Session, old: str, new: str) -> None:
    r = _row()
    if not _verify(r["pw_hash"], old):
        raise AccountError("wrong_password", "Your current password is not right.")
    _check_password_strength(new)
    salt = crypto.b64d(r["kdf_salt"])
    conn().execute("UPDATE account SET pw_hash=?, dek_by_pw=? WHERE id=1",
                   (_ph.hash(new), crypto.seal(crypto.derive_key(new, salt), sess.dek, AAD_DEK)))
    audit("user", "account.password_changed", {})


def profile() -> dict | None:
    r = _row()
    if not r:
        return None
    return {"name": r["name"], "email": r["email"], "pin": bool(r["pin_hash"]), "totp": bool(r["totp_enc"]),
            "created_at": r["created_at"]}


def _reset_for_tests() -> None:
    with _lock:
        _sessions.clear()
    _pin_fail.update(n=0, until=0.0)
    _login_fail.update(n=0, until=0.0)
