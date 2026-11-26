"""Secrets vault for broker keys and bot tokens.

1. The OS keychain via `keyring` (macOS Keychain, Windows Credential Manager, Secret Service on Linux).
2. If no real keychain backend exists (headless Linux, Docker), an encrypted file `<data_dir>/vault.bin`
   sealed with AES-256-GCM. Its key is the account data key (DEK, available while a user is signed in)
   or, for headless servers, a passphrase read from the file named in $NSQ_VAULT_PASSPHRASE_FILE
   (a Docker secret). Secrets are never written to a plain file and never logged.
Backups ("Export my desk") never include anything from the vault.
"""
from __future__ import annotations

import json
import os
import threading
from pathlib import Path

from . import crypto
from .db import data_dir
from .log import get as get_log

SERVICE = "uk.co.nsko.quant"
AAD = b"nsq:vault"
_log = get_log("vault")
_lock = threading.Lock()
_backend_override: str | None = None   # tests: "file"


class VaultLocked(Exception):
    pass


def _keyring():
    if _backend_override == "file" or os.environ.get("NSQ_VAULT_BACKEND") == "file":
        return None
    try:
        import keyring
        from keyring.backends import fail
        kr = keyring.get_keyring()
        name = type(kr).__name__.lower()
        if isinstance(kr, fail.Keyring) or "null" in name or "chainer" in name and not getattr(kr, "backends", None):
            return None
        return keyring
    except Exception:
        return None


def backend() -> str:
    return "os-keychain" if _keyring() else "encrypted-file"


def _file() -> Path:
    return data_dir() / "vault.bin"


def _file_key() -> bytes:
    pf = os.environ.get("NSQ_VAULT_PASSPHRASE_FILE")
    if pf and Path(pf).exists():
        return crypto.derive_key(Path(pf).read_text().strip(), b"nsq-vault-headless")
    from .account import any_session
    s = any_session()
    if s is None:
        raise VaultLocked("Sign in to unlock saved broker keys (no OS keychain on this computer).")
    return s.dek


def _read_file(key: bytes) -> dict:
    f = _file()
    if not f.exists():
        return {}
    return json.loads(crypto.open_(key, f.read_text(), AAD))


def _write_file(key: bytes, data: dict) -> None:
    f = _file()
    tmp = f.with_suffix(".tmp")
    tmp.write_text(crypto.seal(key, json.dumps(data).encode(), AAD))
    try:
        os.chmod(tmp, 0o600)
    except OSError:
        pass
    tmp.replace(f)


def put(name: str, secret: str) -> str:
    kr = _keyring()
    with _lock:
        if kr:
            kr.set_password(SERVICE, name, secret)
        else:
            key = _file_key()
            d = _read_file(key)
            d[name] = secret
            _write_file(key, d)
    _log.info(f"vault: saved secret '{name}' ({backend()})")
    return backend()


def get(name: str) -> str | None:
    kr = _keyring()
    with _lock:
        if kr:
            return kr.get_password(SERVICE, name)
        try:
            return _read_file(_file_key()).get(name)
        except VaultLocked:
            return None


def delete(name: str) -> None:
    kr = _keyring()
    with _lock:
        if kr:
            try:
                kr.delete_password(SERVICE, name)
            except Exception:
                pass
        else:
            key = _file_key()
            d = _read_file(key)
            d.pop(name, None)
            _write_file(key, d)


def names() -> list[str]:
    """Names only, never values. (OS keychains cannot list; we track names in settings.)"""
    from .settings import get as sget
    return list(sget("vault.names", []))


def remember_name(name: str) -> None:
    from .settings import get as sget, set as sset
    n = set(sget("vault.names", []))
    n.add(name)
    sset("vault.names", sorted(n))
