"""Offline Ed25519-signed licence keys (section 4.2).

Format: `NSQ1.<base64url(payload_json)>.<base64url(signature)>`
Payload: {"name", "email", "expiry": "YYYY-MM-DD", "tier": "Standard"|"Pro", "issued": "YYYY-MM-DD", "id"}.
Signed by Ernest's private key with tools/make-licence; only the PUBLIC key ships in the engine
(nsq/licence_key.py). Checks are fully offline.
"""
from __future__ import annotations

import datetime as dt
import json

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from .crypto import b64d
from .licence_key import PUBLIC_KEY_HEX

TIERS = ("Standard", "Pro")
PREFIX = "NSQ1"


def canonical(payload: dict) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()


def check(token: str, *, public_key_hex: str | None = None, today: dt.date | None = None) -> dict:
    """Returns {"status": "valid"|"invalid"|"expired", "reason", "licence"?}. Never raises."""
    today = today or dt.datetime.now(dt.timezone.utc).date()
    try:
        prefix, p64, s64 = (token or "").strip().split(".")
        if prefix != PREFIX:
            return {"status": "invalid", "reason": "Not an NSKO QUANT licence key."}
        raw = b64d(p64)
        pub = Ed25519PublicKey.from_public_bytes(bytes.fromhex(public_key_hex or PUBLIC_KEY_HEX))
        pub.verify(b64d(s64), raw)
        payload = json.loads(raw)
    except InvalidSignature:
        return {"status": "invalid", "reason": "The licence signature does not match. The key was changed or is not genuine."}
    except Exception:
        return {"status": "invalid", "reason": "The licence key is damaged or incomplete."}
    if payload.get("tier") not in TIERS:
        return {"status": "invalid", "reason": "Unknown licence tier."}
    try:
        expiry = dt.date.fromisoformat(payload["expiry"])
    except Exception:
        return {"status": "invalid", "reason": "The licence has no valid expiry date."}
    lic = {k: payload.get(k) for k in ("name", "email", "tier", "expiry", "issued", "id")}
    if today > expiry:
        return {"status": "expired", "reason": f"This licence ended on {expiry.isoformat()}.", "licence": lic}
    return {"status": "valid", "reason": "Licence OK.", "licence": lic, "days_left": (expiry - today).days}
