#!/usr/bin/env python3
"""NSKO QUANT licence maker (for Ernest only).

  python3 tools/make-licence/make_licence.py keygen
      Makes a new Ed25519 keypair. The PRIVATE key goes to tools/keys/licence_private.pem
      (git-ignored, never commit it, back it up somewhere safe offline). The PUBLIC key is
      written into engine/nsq/licence_key.py so the engine can check licences.
      Warning: a new keypair makes every licence signed with the old key invalid.

  python3 tools/make-licence/make_licence.py sign --name "Jane Doe" --email jane@example.com --expiry 2027-12-31 --tier Pro
      Prints a licence key to send to the customer.

  python3 tools/make-licence/make_licence.py verify NSQ1.xxxx.yyyy
      Checks a licence against the public key.

  python3 tools/make-licence/make_licence.py sign-pack pack.json > pack.nsqpack
      Signs an NSKO strategy pack ({"name": ..., "strategies": [recipe, ...]}). Packs install into the Lab only.

Needs only the `cryptography` package (pip install cryptography).
"""
from __future__ import annotations

import argparse
import base64
import datetime as dt
import json
import os
import re
import sys
import uuid
from pathlib import Path

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

ROOT = Path(__file__).resolve().parents[2]          # nsko-quant/
KEYS = ROOT / "tools" / "keys"
PRIV = KEYS / "licence_private.pem"
ENGINE_KEY = ROOT / "engine" / "nsq" / "licence_key.py"
TIERS = ("Standard", "Pro")


def b64e(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).decode().rstrip("=")


def b64d(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def canonical(p: dict) -> bytes:
    return json.dumps(p, sort_keys=True, separators=(",", ":")).encode()


def load_private(path: Path) -> Ed25519PrivateKey:
    if not path.exists():
        sys.exit(f"No private key at {path}. Run `keygen` first (or pass --key).")
    return serialization.load_pem_private_key(path.read_bytes(), password=None)


def make_token(priv: Ed25519PrivateKey, name: str, email: str, expiry: str, tier: str) -> str:
    if tier not in TIERS:
        raise ValueError(f"tier must be one of {TIERS}")
    dt.date.fromisoformat(expiry)
    if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
        raise ValueError("email does not look right")
    payload = {"name": name, "email": email.lower(), "expiry": expiry, "tier": tier,
               "issued": dt.date.today().isoformat(), "id": uuid.uuid4().hex[:12]}
    raw = canonical(payload)
    return f"NSQ1.{b64e(raw)}.{b64e(priv.sign(raw))}"


def cmd_keygen(a) -> None:
    out = Path(a.key)
    if out.exists() and not a.force:
        sys.exit(f"{out} already exists. Use --force to replace it (old licences will stop working).")
    out.parent.mkdir(parents=True, exist_ok=True)
    priv = Ed25519PrivateKey.generate()
    out.write_bytes(priv.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                                       serialization.NoEncryption()))
    try:
        os.chmod(out, 0o600)
    except OSError:
        pass
    pub_hex = priv.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw).hex()
    if not a.no_engine:
        ENGINE_KEY.write_text(
            '"""Public half of the NSKO licence signing key (made by tools/make-licence). Safe to ship."""\n'
            f'PUBLIC_KEY_HEX = "{pub_hex}"\n')
        print(f"Public key written to {ENGINE_KEY}")
    print(f"Private key saved to {out} (keep it secret, back it up offline).")
    print(f"Public key: {pub_hex}")


def cmd_sign(a) -> None:
    print(make_token(load_private(Path(a.key)), a.name, a.email, a.expiry, a.tier))


def cmd_sign_pack(a) -> None:
    pack = json.loads(Path(a.pack).read_text())
    if not isinstance(pack.get("strategies"), list):
        sys.exit("pack.json needs a \"strategies\" list")
    raw = canonical(pack)
    print(f"NSQPACK1.{b64e(raw)}.{b64e(load_private(Path(a.key)).sign(raw))}")


def cmd_verify(a) -> None:
    pub_hex = a.pub
    if not pub_hex:
        m = re.search(r'PUBLIC_KEY_HEX = "([0-9a-f]+)"', ENGINE_KEY.read_text())
        pub_hex = m.group(1)
    try:
        _, p, s = a.token.split(".")
        Ed25519PublicKey.from_public_bytes(bytes.fromhex(pub_hex)).verify(b64d(s), b64d(p))
    except (InvalidSignature, ValueError):
        sys.exit("INVALID: the signature does not match.")
    payload = json.loads(b64d(p))
    expired = dt.date.fromisoformat(payload["expiry"]) < dt.date.today()
    print(("EXPIRED " if expired else "VALID ") + json.dumps(payload, indent=2))


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description="NSKO QUANT licence maker")
    sub = ap.add_subparsers(dest="cmd", required=True)
    k = sub.add_parser("keygen"); k.add_argument("--key", default=str(PRIV)); k.add_argument("--force", action="store_true")
    k.add_argument("--no-engine", action="store_true", help="do not write the public key into the engine")
    s = sub.add_parser("sign"); s.add_argument("--key", default=str(PRIV)); s.add_argument("--name", required=True)
    s.add_argument("--email", required=True); s.add_argument("--expiry", required=True, help="YYYY-MM-DD")
    s.add_argument("--tier", required=True, choices=TIERS)
    v = sub.add_parser("verify"); v.add_argument("token"); v.add_argument("--pub", help="public key hex (default: the engine's)")
    sp = sub.add_parser("sign-pack"); sp.add_argument("pack"); sp.add_argument("--key", default=str(PRIV))
    a = ap.parse_args(argv)
    {"keygen": cmd_keygen, "sign": cmd_sign, "verify": cmd_verify, "sign-pack": cmd_sign_pack}[a.cmd](a)


if __name__ == "__main__":
    main()
