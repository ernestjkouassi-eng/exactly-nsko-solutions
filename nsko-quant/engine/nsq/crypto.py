"""Small crypto helpers: Argon2id key derivation and AES-256-GCM sealing.

Sealed blobs are `base64(version | nonce(12) | ciphertext+tag)`. Associated data binds a blob to
its purpose, so a sealed TOTP secret cannot be swapped in as a vault entry.
"""
from __future__ import annotations

import base64
import os

from argon2.low_level import Type, hash_secret_raw
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

VERSION = b"\x01"
# Argon2id parameters for key derivation (RFC 9106 "second recommended" profile, memory 64 MiB).
KDF_TIME, KDF_MEM_KIB, KDF_PAR = 3, 64 * 1024, 4


def b64e(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).decode()


def b64d(s: str) -> bytes:
    return base64.urlsafe_b64decode(s.encode() + b"=" * (-len(s) % 4))


def derive_key(secret: str | bytes, salt: bytes, *, fast: bool = False) -> bytes:
    """Argon2id -> 32-byte key. `fast` is only for tests (env NSQ_FAST_KDF=1)."""
    if isinstance(secret, str):
        secret = secret.encode()
    t, m = (1, 8 * 1024) if (fast or os.environ.get("NSQ_FAST_KDF") == "1") else (KDF_TIME, KDF_MEM_KIB)
    return hash_secret_raw(secret, salt, time_cost=t, memory_cost=m, parallelism=KDF_PAR, hash_len=32, type=Type.ID)


def seal(key: bytes, plaintext: bytes, aad: bytes = b"") -> str:
    nonce = os.urandom(12)
    return b64e(VERSION + nonce + AESGCM(key).encrypt(nonce, plaintext, aad))


def open_(key: bytes, blob: str, aad: bytes = b"") -> bytes:
    raw = b64d(blob)
    if raw[:1] != VERSION:
        raise ValueError("unknown sealed-blob version")
    return AESGCM(key).decrypt(raw[1:13], raw[13:], aad)


def seal_with_passphrase(passphrase: str, plaintext: bytes, aad: bytes = b"") -> bytes:
    """Self-contained file format: b'NSQ1' | salt(16) | sealed. Used by backups and the vault file."""
    salt = os.urandom(16)
    key = derive_key(passphrase, salt)
    return b"NSQ1" + salt + seal(key, plaintext, aad).encode()


def open_with_passphrase(passphrase: str, data: bytes, aad: bytes = b"") -> bytes:
    if data[:4] != b"NSQ1":
        raise ValueError("not an NSKO QUANT encrypted file")
    salt, blob = data[4:20], data[20:].decode()
    return open_(derive_key(passphrase, salt), blob, aad)
