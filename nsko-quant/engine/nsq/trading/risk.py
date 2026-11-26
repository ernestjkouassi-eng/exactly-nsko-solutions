"""The risk gate. Hard. It cannot be disabled in live mode, and limits cannot be loosened past HARD_CAPS in live.

Every check is written to risk_events (pass or block, with the reason) and a `risk_check` event is published.
"""
from __future__ import annotations

import datetime as dt
import json
import time
from dataclasses import dataclass, field

from ..bus import publish
from ..db import conn
from ..settings import get

# Live can never be looser than these, whatever the settings say.
HARD_CAPS = {"risk.per_trade_pct": 2.0, "risk.daily_loss_pct": 5.0, "risk.weekly_loss_pct": 10.0,
             "risk.max_trades_per_day": 10, "risk.max_open_positions": 4, "risk.max_exposure_per_market_pct": 4.0}


@dataclass
class TradeContext:
    plan_id: str
    market: str
    side: str
    entry: float
    stop: float | None
    target: float | None
    qty: float
    risk_gbp: float                 # loss at the stop for this size
    equity: float
    bid: float | None = None
    ask: float | None = None
    last_data_ts: float | None = None
    broker_online: bool = True
    data_ok: bool = True
    open_positions: list = field(default_factory=list)   # [{market, risk_gbp}]
    mode: str = "paper"
    now: float = field(default_factory=time.time)


@dataclass
class RiskResult:
    passed: bool
    checks: list
    blocked_by: list

    def dict(self) -> dict:
        return {"passed": self.passed, "checks": self.checks, "blocked_by": self.blocked_by}


def limit(key: str, mode: str) -> float:
    v = float(get(key))
    if mode == "live" and key in HARD_CAPS:
        v = min(v, HARD_CAPS[key])
    return v


def gate_enabled(mode: str) -> bool:
    """Live: always on. Paper: on unless the user switched it off for experiments."""
    return True if mode == "live" else bool(get("risk.gate_enabled", True))


def _day_bounds(now: float) -> tuple[float, float]:
    d = dt.datetime.fromtimestamp(now, dt.timezone.utc)
    start = dt.datetime(d.year, d.month, d.day, tzinfo=dt.timezone.utc)
    week = start - dt.timedelta(days=start.weekday())
    return start.timestamp(), week.timestamp()


def realised_since(ts: float, mode: str | None = None) -> float:
    q = "SELECT COALESCE(SUM(pnl),0) AS s FROM journal WHERE ts>=?"
    args: list = [ts]
    if mode:
        q += " AND mode=?"
        args.append(mode)
    return float(conn().execute(q, args).fetchone()["s"])


def trades_since(ts: float, mode: str | None = None) -> int:
    q = "SELECT COUNT(*) AS n FROM trade_plans WHERE created_at>=? AND state IN ('executed','managing','closed')"
    args: list = [ts]
    if mode:
        q += " AND mode=?"
        args.append(mode)
    return int(conn().execute(q, args).fetchone()["n"])


def spread_ok(market: str, bid: float | None, ask: float | None) -> tuple[bool, str]:
    if bid is None or ask is None:
        return False, "no live quote"
    spread = ask - bid
    caps = get("risk.max_spread_points") or {}
    if market in caps:
        cap = float(caps[market])
        return spread <= cap, f"spread {spread:.5g} vs max {cap:.5g}"
    mid = (ask + bid) / 2
    bps = spread / mid * 1e4 if mid else 1e9
    cap = float(get("risk.default_max_spread_bps"))
    return bps <= cap, f"spread {bps:.1f} bps vs max {cap:.1f} bps"


def _norm_asset(a: str) -> str:
    return "".join(ch for ch in str(a).upper() if ch.isalnum())


def godseye_flags(market: str) -> dict:
    """God's Eye MARKET IMPACT risk flags for this market. Only honoured when the user set
    godseye.risk_actions = "apply"; flags can only REDUCE risk: cut_size (smaller trade) or pause_new (no new entry)."""
    out = {"applied": False, "pause": False, "cut": False, "factor": 1.0, "flags": []}
    if get("godseye.risk_actions", "suggest") != "apply":
        return out
    try:
        from ..godseye.impact import active_risk_flags
        flags = [f for f in active_risk_flags() if _norm_asset(f["asset"]) == _norm_asset(market)]
    except Exception:   # God's Eye unavailable: never loosen anything, just report nothing
        return out
    out.update(applied=True, flags=flags, pause=any(f["action"] == "pause_new" for f in flags),
               cut=any(f["action"] == "cut_size" for f in flags))
    if out["cut"]:
        out["factor"] = min(1.0, max(0.0, float(get("godseye.cut_size_factor", 0.5) or 0.5)))
    return out


def check(ctx: TradeContext, record: bool = True) -> RiskResult:
    from .killswitch import is_locked
    m = ctx.mode
    checks: list[dict] = []

    def add(rule: str, ok: bool, reason: str) -> None:
        checks.append({"rule": rule, "passed": bool(ok), "reason": reason})

    locked, why = is_locked()
    add("trading_unlocked", not locked, why or "trading enabled")
    add("stop_and_target", ctx.stop is not None and ctx.target is not None, "every trade needs a stop and a target")
    stale_s = float(get("risk.stale_data_s"))
    age = (ctx.now - ctx.last_data_ts) if ctx.last_data_ts else None
    add("fresh_data", ctx.data_ok and age is not None and age <= stale_s,
        f"last data {age:.0f}s old (max {stale_s:.0f}s)" if age is not None else "no data timestamp")
    add("broker_online", ctx.broker_online, "broker connected" if ctx.broker_online else "broker offline: no new entries")
    ok, why = spread_ok(ctx.market, ctx.bid, ctx.ask)
    add("spread", ok, why)
    add("size_positive", ctx.qty > 0, f"size {ctx.qty}")
    per = limit("risk.per_trade_pct", m)
    max_risk = ctx.equity * per / 100
    add("per_trade_risk", ctx.risk_gbp <= max_risk * 1.0001, f"£{ctx.risk_gbp:.2f} at risk vs max £{max_risk:.2f} ({per}%)")
    day0, week0 = _day_bounds(ctx.now)
    day_pnl, week_pnl = realised_since(day0, m), realised_since(week0, m)
    dl, wl = limit("risk.daily_loss_pct", m), limit("risk.weekly_loss_pct", m)
    add("daily_loss", day_pnl > -ctx.equity * dl / 100, f"today £{day_pnl:.2f} vs stop at -{dl}%")
    add("weekly_loss", week_pnl > -ctx.equity * wl / 100, f"this week £{week_pnl:.2f} vs stop at -{wl}%")
    mt = int(limit("risk.max_trades_per_day", m))
    n = trades_since(day0, m)
    add("max_trades_day", n < mt, f"{n} trades today (max {mt})")
    mo = int(limit("risk.max_open_positions", m))
    add("max_open_positions", len(ctx.open_positions) < mo, f"{len(ctx.open_positions)} open (max {mo})")
    me = limit("risk.max_exposure_per_market_pct", m)
    exp = sum(float(p.get("risk_gbp", 0)) for p in ctx.open_positions if p.get("market") == ctx.market) + ctx.risk_gbp
    add("market_exposure", exp <= ctx.equity * me / 100 * 1.0001, f"£{exp:.2f} on {ctx.market} vs max {me}% of equity")
    ge = godseye_flags(ctx.market)
    if ge["applied"]:
        why = "; ".join(f"{f['action']} ({f['impact_id'].split(':')[0]})" for f in ge["flags"]) or "no God's Eye flag on this market"
        add("godseye_flags", not ge["pause"], ("God's Eye paused new entries: " if ge["pause"] else "God's Eye: ") + why)

    enforced = gate_enabled(m)
    blocked = [c for c in checks if not c["passed"]]
    passed = not blocked or not enforced
    if blocked and not enforced:
        for c in checks:
            c["note"] = "gate switched off (paper only)"
    res = RiskResult(passed, checks, [c["rule"] for c in blocked])
    if record:
        c = conn()
        for ch in checks:
            if not ch["passed"] or ch["rule"] in ("per_trade_risk",):
                c.execute("INSERT INTO risk_events (ts, plan_id, market, rule, passed, reason, detail) VALUES (?,?,?,?,?,?,?)",
                          (time.time(), ctx.plan_id, ctx.market, ch["rule"], int(ch["passed"]), ch["reason"],
                           json.dumps({"mode": m, "enforced": enforced})))
        if not blocked:
            c.execute("INSERT INTO risk_events (ts, plan_id, market, rule, passed, reason, detail) VALUES (?,?,?,?,?,?,?)",
                      (time.time(), ctx.plan_id, ctx.market, "all", 1, "all checks passed", json.dumps({"mode": m})))
        publish("risk_check", {"plan_id": ctx.plan_id, "market": ctx.market, "passed": passed, "checks": checks,
                               "blocked_by": res.blocked_by, "mode": m, "demo": False})
        if blocked and enforced:
            publish("ticker_log", {"verb": "RISK", "msg": f"{ctx.market} blocked: " + "; ".join(c["reason"] for c in blocked)})
        if "daily_loss" in res.blocked_by:
            from ..settings import set as sset
            sset("trading.day_stop", dt.datetime.fromtimestamp(ctx.now, dt.timezone.utc).date().isoformat())
    return res
