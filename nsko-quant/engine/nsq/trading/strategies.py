"""Strategy lifecycle and updates (section 9.8).

- Every change is a new row in strategy_versions; every change is audited.
- Status: lab -> paper -> live (or retired). The scanner only uses approved strategies (paper or live).
- Manual update: edit rules -> re-run the lab -> promote.
- Automatic update: a variant that beats the live version on out-of-sample metrics by a margin goes to PAPER;
  promotion to live is "auto" or "ask" (a decision_needed event).
- Live never changes mid-trade: a live promotion or rollback while the strategy has an open position is
  queued and applied when it is flat.
- One-click rollback to the previous version.
- NSKO signed strategy packs (Ed25519, same NSKO public key as licences) install into the Lab only.
"""
from __future__ import annotations

import json
import time
import uuid

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from ..audit import audit
from ..bus import publish
from ..crypto import b64d
from ..db import conn
from ..licence_key import PUBLIC_KEY_HEX
from ..settings import get


class StrategyError(Exception):
    pass


def _now() -> float:
    return time.time()


def create(recipe: dict, source: str = "lab", status: str = "lab", metrics: dict | None = None, actor: str = "user") -> str:
    sid = recipe.get("id") or f"st-{uuid.uuid4().hex[:8]}"
    recipe = {**recipe, "id": sid}
    c = conn()
    c.execute("INSERT INTO strategies (id, name, market, timeframe, status, intraday, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?)",
              (sid, recipe.get("name", sid), recipe.get("market", ""), recipe.get("timeframe", "15m"), "lab",
               int(recipe.get("intraday", True)), _now(), _now()))
    add_version(sid, recipe, source, metrics, "created", actor=actor)
    if status != "lab":
        promote(sid, status, actor=actor)
    return sid


def add_version(sid: str, recipe: dict, source: str, metrics: dict | None = None, note: str = "", actor: str = "user") -> int:
    c = conn()
    v = (c.execute("SELECT MAX(version) v FROM strategy_versions WHERE strategy_id=?", (sid,)).fetchone()["v"] or 0) + 1
    c.execute("INSERT INTO strategy_versions (strategy_id, version, json_rules, source, metrics, note, created_at) VALUES (?,?,?,?,?,?,?)",
              (sid, v, json.dumps({**recipe, "id": sid}), source, json.dumps(metrics or {}), note, _now()))
    audit(actor, "strategy.version", {"strategy_id": sid, "version": v, "source": source, "note": note})
    return v


def get_strategy(sid: str) -> dict:
    r = conn().execute("SELECT * FROM strategies WHERE id=?", (sid,)).fetchone()
    if not r:
        raise StrategyError(f"no strategy {sid}")
    return r


def versions(sid: str) -> list[dict]:
    rows = conn().execute("SELECT * FROM strategy_versions WHERE strategy_id=? ORDER BY version", (sid,)).fetchall()
    for r in rows:
        r["json_rules"], r["metrics"] = json.loads(r["json_rules"]), json.loads(r["metrics"] or "{}")
    return rows


def recipe(sid: str, version: int | None = None) -> dict:
    s = get_strategy(sid)
    v = version or s["live_version"] or s["paper_version"] or conn().execute(
        "SELECT MAX(version) v FROM strategy_versions WHERE strategy_id=?", (sid,)).fetchone()["v"]
    r = conn().execute("SELECT json_rules FROM strategy_versions WHERE strategy_id=? AND version=?", (sid, v)).fetchone()
    if not r:
        raise StrategyError(f"{sid} has no version {v}")
    return {**json.loads(r["json_rules"]), "_version": v}


def has_open_position(sid: str) -> bool:
    return conn().execute("SELECT 1 FROM positions WHERE strategy_id=? AND status='open' LIMIT 1", (sid,)).fetchone() is not None


def promote(sid: str, to: str, version: int | None = None, actor: str = "user") -> dict:
    if to not in ("paper", "live", "lab", "retired"):
        raise StrategyError("promote to paper, live, lab or retired")
    s = get_strategy(sid)
    v = version or conn().execute("SELECT MAX(version) v FROM strategy_versions WHERE strategy_id=?", (sid,)).fetchone()["v"]
    c = conn()
    if to == "live":
        if has_open_position(sid):
            c.execute("UPDATE strategies SET updated_at=? WHERE id=?", (_now(), sid))
            from ..settings import set as sset
            sset(f"strategy.pending_live.{sid}", v)
            audit(actor, "strategy.promote_queued", {"strategy_id": sid, "version": v, "why": "open position: live never changes mid-trade"})
            return {"queued": True, "version": v}
        c.execute("UPDATE strategies SET status='live', live_version=?, updated_at=? WHERE id=?", (v, _now(), sid))
    elif to == "paper":
        c.execute("UPDATE strategies SET status=CASE WHEN status='live' THEN 'live' ELSE 'paper' END, paper_version=?, updated_at=? WHERE id=?",
                  (v, _now(), sid))
    else:
        c.execute("UPDATE strategies SET status=?, updated_at=? WHERE id=?", (to, _now(), sid))
    audit(actor, "strategy.promote", {"strategy_id": sid, "to": to, "version": v, "from": s["status"]})
    publish("strategy_status", {"id": sid, "status": to, "version": v})
    return {"queued": False, "version": v, "status": to}


def apply_pending(sid: str) -> bool:
    """Called when a strategy goes flat: apply a queued live change."""
    from ..settings import get as sget, set as sset
    v = sget(f"strategy.pending_live.{sid}", None)
    if v is None or has_open_position(sid):
        return False
    conn().execute("UPDATE strategies SET status='live', live_version=?, updated_at=? WHERE id=?", (v, _now(), sid))
    sset(f"strategy.pending_live.{sid}", None)
    audit("engine", "strategy.promote_applied", {"strategy_id": sid, "version": v})
    publish("strategy_status", {"id": sid, "status": "live", "version": v})
    return True


def rollback(sid: str, actor: str = "user") -> dict:
    """One click: the active version (live if live, else paper) goes back to the version before it."""
    s = get_strategy(sid)
    field = "live_version" if s["status"] == "live" else "paper_version"
    cur = s[field]
    prev = conn().execute("SELECT MAX(version) v FROM strategy_versions WHERE strategy_id=? AND version<?",
                          (sid, cur or 0)).fetchone()["v"]
    if not prev:
        raise StrategyError("nothing to roll back to")
    if field == "live_version" and has_open_position(sid):
        from ..settings import set as sset
        sset(f"strategy.pending_live.{sid}", prev)
        audit(actor, "strategy.rollback_queued", {"strategy_id": sid, "from": cur, "to": prev})
        return {"queued": True, "from": cur, "to": prev}
    conn().execute(f"UPDATE strategies SET {field}=?, updated_at=? WHERE id=?", (prev, _now(), sid))
    audit(actor, "strategy.rollback", {"strategy_id": sid, "field": field, "from": cur, "to": prev})
    publish("strategy_status", {"id": sid, "status": s["status"], "version": prev, "rollback": True})
    return {"queued": False, "from": cur, "to": prev}


def manual_update(sid: str, new_rules: dict, lab_metrics: dict | None = None, actor: str = "user") -> int:
    """Edit rules -> (caller re-runs the lab, passes metrics) -> new version in the Lab. Promote separately."""
    v = add_version(sid, new_rules, "manual", lab_metrics, "manual edit", actor=actor)
    return v


def auto_update(sid: str, variant_rules: dict, variant_metrics: dict, live_metrics: dict) -> dict:
    margin = float(get("updates.auto_margin_sharpe"))
    better = float(variant_metrics.get("sharpeOOS", 0)) >= float(live_metrics.get("sharpeOOS", 0)) + margin
    if not better:
        audit("engine", "strategy.auto_update_rejected", {"strategy_id": sid, "variant": variant_metrics.get("sharpeOOS"),
                                                          "live": live_metrics.get("sharpeOOS"), "margin": margin})
        return {"accepted": False, "why": f"variant does not beat live OOS Sharpe by {margin}"}
    v = add_version(sid, variant_rules, "auto", variant_metrics, f"beat live OOS by >= {margin}", actor="engine")
    promote(sid, "paper", v, actor="engine")
    mode = get("updates.promote_live")
    if mode == "auto":
        r = promote(sid, "live", v, actor="engine")
        return {"accepted": True, "version": v, "live": not r["queued"], "queued": r["queued"]}
    publish("decision_needed", {"id": f"promote-{sid}-{v}", "tag": "TO LIVE", "title": f"{sid} v{v}",
                                "desc": f"Sharpe OOS {variant_metrics.get('sharpeOOS')} vs live {live_metrics.get('sharpeOOS')}. Paper first, then you decide."})
    return {"accepted": True, "version": v, "live": False, "asked": True}


def approved(mode: str | None = None) -> list[dict]:
    """Strategies the scanner may trade: paper and live ones. (Live mode uses only live ones.)"""
    mode = mode or get("mode")
    statuses = ("live",) if mode == "live" else ("paper", "live")
    rows = conn().execute(f"SELECT * FROM strategies WHERE status IN ({','.join('?' * len(statuses))})", statuses).fetchall()
    out = []
    for s in rows:
        v = s["live_version"] if mode == "live" else (s["paper_version"] or s["live_version"])
        out.append({**s, "recipe": recipe(s["id"], v)})
    return out


# ------------------------------------------------------------------ signed packs
PACK_PREFIX = "NSQPACK1"


def install_pack(token: str, public_key_hex: str | None = None) -> list[str]:
    """`NSQPACK1.<b64 json {"name", "strategies": [recipe, ...]}>.<b64 sig>` signed by NSKO. Lab only."""
    try:
        prefix, p64, s64 = token.strip().split(".")
        assert prefix == PACK_PREFIX
        raw = b64d(p64)
        Ed25519PublicKey.from_public_bytes(bytes.fromhex(public_key_hex or PUBLIC_KEY_HEX)).verify(b64d(s64), raw)
    except (InvalidSignature, AssertionError, ValueError) as e:
        audit("user", "strategy.pack_rejected", {"why": type(e).__name__})
        raise StrategyError("This strategy pack is not signed by NSKO. Not installed.") from e
    pack = json.loads(raw)
    ids = []
    for r in pack.get("strategies", []):
        rid = f"pack-{r['id']}" if r.get("id") else None
        if rid and conn().execute("SELECT 1 FROM strategies WHERE id=?", (rid,)).fetchone():
            rid = f"{rid}-{uuid.uuid4().hex[:4]}"
        sid = create({**r, "id": rid}, source=f"pack:{pack.get('name', '?')}", status="lab", actor="pack")
        ids.append(sid)
    audit("user", "strategy.pack_installed", {"name": pack.get("name"), "count": len(ids)})
    return ids
