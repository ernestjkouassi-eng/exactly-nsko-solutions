"""The trade flow (section 9). For every trade:

SCANNER -> NEWS/EVENTS CHECK -> FORECAST -> ENTRY TRIGGER -> TIME MACHINE -> SIZE -> RISK GATE
-> (multi-agent debate: veto only) -> EXECUTE (bracket) -> MANAGE (scale-out, trail) -> EXIT -> JOURNAL + ALERT

Each step publishes its event (scan_hit, news_hit, forecast_done, entry_state, timemachine_progress/_done,
size_calc, risk_check, order_sent, order_filled, position_update, exit_done, alert).
Modes: "auto" runs every step; "manual" pauses at EXECUTE for /trade/approve (60 s, default = skip).
Closed bars only: the bar that is still forming is dropped before signals or entry are computed.
"""
from __future__ import annotations

import json
import threading
import time
import uuid

import pandas as pd

from ..audit import audit
from ..brokers import active
from ..brokers.base import BrokerAdapter, BrokerError, value_per_point
from ..bus import publish
from ..db import conn
from ..settings import get
from . import debate, forecast, live_unlock, news, risk, sizing, timemachine
from .execute import execute_bracket
from .manage import Manager
from .synthetic import tf_minutes

_approvals: dict[str, dict] = {}
_alock = threading.Lock()


def approve(plan_id: str, decision: str = "approve") -> bool:
    """Called by POST /trade/approve. decision: approve | skip."""
    with _alock:
        a = _approvals.get(plan_id)
        if not a:
            return False
        a["decision"] = decision
        a["event"].set()
    audit("user", "trade.approval", {"plan_id": plan_id, "decision": decision})
    return True


def pending_approvals() -> list[str]:
    with _alock:
        return list(_approvals)


def signals_generate(recipe: dict, df: pd.DataFrame) -> list[dict]:
    try:
        from ..lab import signals as lab_signals
        return lab_signals.generate(recipe, df)
    except ImportError:
        from . import signals_fallback
        return signals_fallback.generate(recipe, df)


def closed_bars(df: pd.DataFrame, timeframe: str, now: pd.Timestamp | None = None) -> pd.DataFrame:
    """Drop any bar that has not closed yet (index = bar open time)."""
    if df is None or df.empty:
        return df
    now = now if now is not None else pd.Timestamp.now(tz="UTC")
    if now.tzinfo is None:
        now = now.tz_localize("UTC")
    end_of_bar = df.index + pd.Timedelta(minutes=tf_minutes(timeframe))
    out = df[end_of_bar <= now]
    out.attrs.update(df.attrs)
    return out


class TradeFlow:
    def __init__(self, broker: BrokerAdapter | None = None, candles_fn=None, signals_fn=None, use_llm: bool | None = False):
        self.broker = broker or active()
        self.candles_fn = candles_fn
        self.signals_fn = signals_fn or signals_generate
        self.manager = Manager(self.broker)
        self.use_llm = use_llm

    # ------------------------------------------------------------------ helpers
    def _candles(self, market: str, tf: str, now: pd.Timestamp) -> pd.DataFrame:
        start = now - pd.Timedelta(minutes=tf_minutes(tf) * 600)
        if self.candles_fn:
            return self.candles_fn(market, tf, start, now)
        try:
            from ..data import candles as data_candles
            return data_candles.get(market, tf, start, now)
        except Exception:
            return self.broker.candles(market, tf, start, now)

    def _plan_row(self, plan: dict, state: str, detail: dict | None = None) -> None:
        now = time.time()
        conn().execute(
            "INSERT INTO trade_plans (id, strategy_id, market, side, entry, stop, target, size, state, mode, detail, created_at, updated_at)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET state=excluded.state, size=excluded.size,"
            " entry=excluded.entry, detail=excluded.detail, updated_at=excluded.updated_at",
            (plan["id"], plan.get("strategy_id"), plan["market"], plan.get("side"), plan.get("entry"), plan.get("stop"),
             plan.get("target"), plan.get("qty"), state, plan.get("mode"), json.dumps(detail or {}, default=str), now, now))

    def _skip(self, plan: dict, step: str, why: str, steps: list) -> dict:
        self._plan_row(plan, "skipped", {"step": step, "why": why})
        publish("ticker_log", {"verb": "REJECT", "msg": f"{plan['market']} {step}: {why}", "plan_id": plan["id"],
                               "step": step, "why": why})
        return {"plan_id": plan["id"], "result": "skipped", "step": step, "why": why, "steps": steps}

    # ------------------------------------------------------------------ the flow
    def run(self, strategy: dict, now: pd.Timestamp | None = None, df: pd.DataFrame | None = None,
            manual_timeout_s: float | None = None) -> dict:
        """Run the full flow once for one approved strategy. Returns what happened at each step."""
        now = now if now is not None else pd.Timestamp.now(tz="UTC")
        mode = get("mode")
        trade_mode = get("trade_mode")
        rec = strategy["recipe"]
        market, tf = rec["market"], rec.get("timeframe", "15m")
        plan = {"id": uuid.uuid4().hex[:12], "strategy_id": strategy["id"], "market": market, "mode": mode,
                "intraday": bool(strategy.get("intraday", 1))}
        steps: list = []

        # 1. SCANNER (approved strategies only)
        if strategy.get("status") not in ("paper", "live") or (mode == "live" and strategy.get("status") != "live"):
            return {"result": "skipped", "step": "scanner", "why": "strategy not approved for this mode", "steps": steps}
        if get("trading.paused", False):
            return {"result": "skipped", "step": "scanner", "why": "new trades are paused", "steps": steps}
        if mode == "live" and not live_unlock.is_unlocked():
            return {"result": "skipped", "step": "scanner", "why": "live is locked: finish the live checklist", "steps": steps}
        raw = df if df is not None else self._candles(market, tf, now)
        bars = closed_bars(raw, tf, now)
        if bars is None or len(bars) < 50:
            return {"result": "skipped", "step": "scanner", "why": "not enough closed bars", "steps": steps}
        sigs = [s for s in self.signals_fn(rec, bars) if pd.Timestamp(s["time"]) == bars.index[-1]]
        if not sigs:
            return {"result": "no_signal", "step": "scanner", "steps": steps}
        sig = sigs[-1]
        plan.update(side=sig["side"], stop=float(sig["stop"]), target=float(sig["target"]), signal_entry=float(sig["entry"]),
                    signal_time=str(sig["time"]))
        synthetic = bool(bars.attrs.get("synthetic"))
        publish("scan_hit", {"plan_id": plan["id"], "strategy": strategy["id"], "market": market, "tf": tf, "side": sig["side"],
                             "reason": sig.get("reason"), "bar": str(bars.index[-1]), "synthetic": synthetic})
        steps.append("scanner")
        self._plan_row(plan, "pending")

        # 2. NEWS / EVENTS
        nc = news.check(market, now.to_pydatetime(), rec.get("filters", {}).get("news_blackout_min"))
        publish("news_hit", {"plan_id": plan["id"], **nc})
        steps.append("news")
        if nc["blackout"]:
            return self._skip(plan, "news", f"high-impact event within ±{nc['window_min']:.0f} min: {nc['events'][0]['title']}", steps)

        # 3. FORECAST
        fc = forecast.forecast(bars, sig["side"], entry=float(bars["close"].iloc[-1]))
        publish("forecast_done", {"plan_id": plan["id"], **{k: v for k, v in fc.items() if k != "sample"}})
        steps.append("forecast")
        if not fc["passed"]:
            return self._skip(plan, "forecast", f"only {fc['agree_pct']}% of paths agree (need {fc['need_pct']}%)", steps)

        # 4. ENTRY TRIGGER (closed bar t gave the signal; we enter at the live quote now, never at bar t's prices)
        publish("entry_state", {"plan_id": plan["id"], "state": "waiting", "market": market})
        try:
            q = self.broker.ticks(market)
        except BrokerError:
            if not hasattr(self.broker, "set_price"):
                return self._skip(plan, "entry", "no live quote", steps)
            self.broker.set_price(market, float(bars["close"].iloc[-1]), ts=(bars.index[-1] + pd.Timedelta(minutes=tf_minutes(tf))).timestamp())
            q = self.broker.ticks(market)
        entry = q["ask"] if sig["side"] == "buy" else q["bid"]
        plan["entry"] = entry
        if (sig["side"] == "buy" and not (plan["stop"] < entry < plan["target"])) or \
           (sig["side"] == "sell" and not (plan["target"] < entry < plan["stop"])):
            return self._skip(plan, "entry", "price already beyond stop or target", steps)
        publish("entry_state", {"plan_id": plan["id"], "state": "triggered", "market": market, "entry": entry,
                                "stop": plan["stop"], "target": plan["target"], "closed_bar": str(bars.index[-1])})
        steps.append("entry")

        # 5. TIME MACHINE
        left = timemachine.bars_left_in_session(market, bars.index[-1] + pd.Timedelta(minutes=tf_minutes(tf)), tf_minutes(tf),
                                                plan["intraday"])
        tm = timemachine.run(bars, sig["side"], entry, plan["stop"], plan["target"], left, market=market, plan_id=plan["id"])
        steps.append("timemachine")
        if not tm["passed"]:
            return self._skip(plan, "timemachine", f"no edge after costs: P(target) {tm['p_target']}% vs P(stop) {tm['p_stop']}%", steps)

        # 6. SIZE
        acct = self.broker.account()
        ge = risk.godseye_flags(market)            # God's Eye "cut_size" can only make the trade smaller
        sz = sizing.size_trade(acct.equity, float(get("risk.per_trade_pct")), entry, plan["stop"], market,
                               size_factor=live_unlock.size_factor(mode) * ge["factor"])
        if ge["cut"]:
            sz["godseye_cut"] = ge["factor"]
        plan["qty"] = sz["qty"]
        publish("size_calc", {"plan_id": plan["id"], "equity": acct.equity, "currency": acct.currency, **sz, "paper": mode == "paper"})
        steps.append("size")
        self._plan_row(plan, "sizing", {"size": sz})

        # 7. RISK GATE (hard)
        open_pos = [{"market": p.market, "risk_gbp": abs(p.entry - (p.stop or p.entry)) * p.qty * value_per_point(p.market)}
                    for p in self.broker.positions()]
        from ..connectivity import is_online
        ctx = risk.TradeContext(plan["id"], market, sig["side"], entry, plan["stop"], plan["target"], plan["qty"],
                                sz.get("risk_at_stop", 0.0), acct.equity, q["bid"], q["ask"], q.get("ts") or now.timestamp(),
                                self.broker.online() and is_online(), True, open_pos, mode, now.timestamp())
        rr = risk.check(ctx)
        steps.append("risk")
        if not rr.passed:
            return self._skip(plan, "risk", "; ".join(c["reason"] for c in rr.checks if not c["passed"]), steps)

        # multi-agent decision: may veto, can never override the gate
        trend = float(bars["close"].iloc[-1]) > float(bars["close"].tail(50).mean())
        facts = {"market": market, "side": sig["side"], "forecast_agree_pct": fc["agree_pct"], "tm_ev_pts": tm["ev_pts"],
                 "p_target": tm["p_target"], "p_stop": tm["p_stop"],
                 "rr": abs(plan["target"] - entry) / abs(entry - plan["stop"]),
                 "trend_with_trade": trend if sig["side"] == "buy" else not trend,
                 "spread_frac": (q["ask"] - q["bid"]) / abs(entry - plan["stop"])}
        dec = debate.decide(facts, plan["id"], risk_passed=True, use_llm=self.use_llm)
        steps.append("debate")
        if dec["verdict"] == "veto":
            return self._skip(plan, "debate", dec["trader"], steps)

        # 8. EXECUTE (auto, or manual approval with a 60 s timeout whose default is skip)
        if trade_mode == "manual":
            ev = threading.Event()
            with _alock:
                _approvals[plan["id"]] = {"event": ev, "decision": None}
            self._plan_row(plan, "awaiting_approval")
            timeout = float(manual_timeout_s if manual_timeout_s is not None else get("manual_timeout_s"))
            publish("decision_needed", {"id": plan["id"], "plan_id": plan["id"], "tag": "APPROVE TRADE", "title": f"{sig['side'].upper()} {market}",
                                        "desc": f"entry {entry:.5g} · stop {plan['stop']:.5g} · target {plan['target']:.5g} · size {plan['qty']}",
                                        "timeout_s": timeout, "default": "skip"})
            ev.wait(timeout)
            with _alock:
                decision = _approvals.pop(plan["id"], {}).get("decision")
            if decision != "approve":
                return self._skip(plan, "execute", "not approved in time (default: skip)" if decision is None else "skipped by you", steps)
        from .killswitch import is_locked
        if is_locked()[0]:
            return self._skip(plan, "execute", "trading locked", steps)
        ex = execute_bracket(self.broker, plan)
        steps.append("execute")
        if not ex["ok"]:
            self._plan_row(plan, "failed", ex)
            return {"plan_id": plan["id"], "result": "failed", "step": "execute", "why": ex.get("error"), "execution": ex, "steps": steps}
        plan["fill_price"] = ex["fill_price"]
        self._plan_row(plan, "executed", {"execution": ex})
        conn().execute("UPDATE positions SET plan_id=?, strategy_id=?, mode=? WHERE id=?",
                       (plan["id"], strategy["id"], mode, ex["position_id"]))

        # 9. MANAGE
        session_end = None
        if plan["intraday"] and timemachine.spec(market).session != "24x7":
            session_end = (bars.index[-1] + pd.Timedelta(minutes=tf_minutes(tf) * (left + 1))).timestamp()
        self.manager.track(ex["position_id"], plan, soft_target=ex["soft_target"], session_end=session_end)
        self._plan_row(plan, "managing", {"execution": ex})
        audit("engine", "trade.open", {"plan_id": plan["id"], "market": market, "side": sig["side"], "qty": plan["qty"],
                                        "entry": ex["fill_price"], "stop": plan["stop"], "target": plan["target"], "mode": mode})
        from ..notify import notify
        notify("trade", f"{'PAPER' if mode == 'paper' else 'LIVE'} {sig['side'].upper()} {market}",
               f"size {plan['qty']} @ {ex['fill_price']:.5g} · stop {plan['stop']:.5g} · target {plan['target']:.5g}")
        return {"plan_id": plan["id"], "result": "executed", "position_id": ex["position_id"], "plan": plan, "execution": ex,
                "forecast": {k: v for k, v in fc.items() if k not in ("sample", "fan")}, "timemachine": tm, "size": sz,
                "risk": rr.dict(), "debate": dec, "news": nc, "steps": steps + ["manage"]}

    def on_price(self, market: str, price: float, high: float | None = None, low: float | None = None,
                 now: float | None = None) -> list[dict]:
        """Feed a new price: the paper broker triggers its stops/targets, then the manager runs."""
        if hasattr(self.broker, "set_price"):
            self.broker.set_price(market, price, ts=now, high=high, low=low)
        exits = self.manager.on_price(market, price, now=now)
        from .strategies import apply_pending
        for e in exits:
            row = conn().execute("SELECT strategy_id FROM trade_plans WHERE id=?", (e["plan_id"],)).fetchone()
            if row and row["strategy_id"]:
                apply_pending(row["strategy_id"])
        return exits

    def scan_all(self, now: pd.Timestamp | None = None) -> list[dict]:
        from .strategies import approved
        return [self.run(s, now=now) for s in approved()]
