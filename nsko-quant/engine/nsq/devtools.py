"""Development-only endpoints. Mounted ONLY when the engine runs with NSQ_DEV=1 (never in a shipped build).

POST /dev/run-demo-trade runs one full paper trade through the real trade flow (scanner -> news -> forecast ->
entry -> Time Machine -> size -> risk gate -> debate -> execute -> manage -> exit), so the desk's Trade Card,
Manual approval and the journal can be tested end to end without waiting for a real market setup.

What is NOT real here, and says so in every payload and log line:
- the candles are a seeded synthetic up-trend (flagged synthetic=True);
- the signal is a test generator: a long on the last closed bar (the same one the engine tests use);
- after the fill, the price is walked up to 1R and then to the target so the exit steps can be seen.
Everything else (paper broker, sizing, risk gate, bracket orders, journal, audit, alerts) is the real code.
"""
from __future__ import annotations

import os
import threading
import time

import numpy as np
import pandas as pd
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from .bus import publish

router = APIRouter(prefix="/dev", tags=["dev"])
DEV_SID = "dev-demo-xau"
_state: dict = {"running": False, "last": None}


def enabled() -> bool:
    return os.environ.get("NSQ_DEV") == "1"


def trend_candles(end: pd.Timestamp, n: int = 400, tf_min: int = 15, px0: float = 2648.4, seed: int = 3) -> pd.DataFrame:
    """Seeded synthetic up-trend of CLOSED bars ending at `end` (bar open time). Same maths as the engine tests."""
    rng = np.random.default_rng(seed)
    rets = rng.normal(0.0006, 0.0012, n)
    close = px0 * np.exp(np.cumsum(rets))
    open_ = np.concatenate([[px0], close[:-1]])
    wig = np.abs(rng.normal(0, 0.0012 / 3, n)) * close
    idx = pd.date_range(end=end, periods=n, freq=f"{tf_min}min", tz="UTC")
    df = pd.DataFrame({"open": open_, "high": np.maximum(open_, close) + wig, "low": np.minimum(open_, close) - wig,
                       "close": close, "volume": rng.lognormal(5, .5, n)}, index=idx)
    df.attrs.update(synthetic=True, source="dev synthetic trend", volume_kind="synthetic")
    return df


def last_bar_signal(recipe, df):
    """Test generator: a long on the LAST CLOSED bar, stop 2 ATR below, target 4 ATR above."""
    a = float((df["high"] - df["low"]).rolling(14).mean().iloc[-1])
    e = float(df["close"].iloc[-1])
    return [{"time": df.index[-1], "side": "buy", "entry": e, "stop": e - a * 2, "target": e + a * 4,
             "reason": "dev test signal (last closed bar)"}]


def ensure_strategy() -> dict:
    """A paper strategy with two versions, so promote / rollback can be tried on the desk."""
    from .db import conn
    from .lab import seed
    from .trading import strategies as st
    seed.seed_pack()
    if conn().execute("SELECT 1 FROM strategies WHERE id=?", (DEV_SID,)).fetchone() is None:
        rules = {"id": DEV_SID, "name": "Dev demo XAU", "market": "XAU/USD", "timeframe": "15m", "idea_type": "Trend following",
                 "intraday": False, "entry": {"type": "ema_cross"}, "stop": {"type": "atr", "mult": 2.0},
                 "target": {"type": "r", "r": 2.0}, "filters": {"session": None, "news_blackout_min": 15},
                 "params": {"fast": 20, "slow": 50, "atr_n": 14}}
        st.create(rules, source="dev", actor="dev")
        st.add_version(DEV_SID, {**rules, "params": {**rules["params"], "fast": 18}}, "dev", {"sharpeOOS": 1.52},
                       "Faster EMA: 20 → 18", actor="dev")
        st.promote(DEV_SID, "paper", actor="dev")
    row = st.get_strategy(DEV_SID)
    if row["status"] not in ("paper", "live"):
        st.promote(DEV_SID, "paper", actor="dev")
    return {**st.get_strategy(DEV_SID), "recipe": st.recipe(DEV_SID, st.active_version(st.get_strategy(DEV_SID)))}


class DemoTrade(BaseModel):
    walk_to_exit: bool = True       # after the fill, walk the price to 1R and then the target
    step_s: float = 3.0             # seconds between the walked prices
    manual_timeout_s: float | None = None


def _run(req: DemoTrade) -> None:
    from .brokers import active
    from .settings import get
    from .trading.flow import TradeFlow
    try:
        b = active()
        if not hasattr(b, "set_price"):
            raise RuntimeError("the demo trade runs on the paper broker only")
        strat = ensure_strategy()
        now = pd.Timestamp.now(tz="UTC")
        last_open = now.floor("15min") - pd.Timedelta(minutes=15)      # the last bar that has CLOSED
        df = trend_candles(last_open)
        px = float(df["close"].iloc[-1])
        b.set_price("XAU/USD", px, ts=now.timestamp())
        publish("ticker_log", {"verb": "TEST", "msg": "DEV demo trade: synthetic candles + test signal, real paper flow"})
        flow = TradeFlow(b, signals_fn=last_bar_signal, use_llm=False)
        timeout = req.manual_timeout_s if req.manual_timeout_s is not None else float(get("manual_timeout_s"))
        r = flow.run(strat, now=now, df=df, manual_timeout_s=timeout)
        _state["last"] = {k: v for k, v in r.items() if k in ("plan_id", "result", "step", "why", "steps")}
        if r.get("result") == "executed" and req.walk_to_exit:
            entry, stop, target = r["execution"]["fill_price"], r["plan"]["stop"], r["plan"]["target"]
            for p in (entry + (entry - stop) * 0.5, entry + (entry - stop) * 1.05, (entry + target) / 2, target + 0.5):
                time.sleep(req.step_s)
                flow.on_price("XAU/USD", p, now=time.time())
            _state["last"]["exit"] = True
    except Exception as e:   # report, never crash the engine
        _state["last"] = {"result": "error", "why": f"{type(e).__name__}: {e}"}
        publish("ticker_log", {"verb": "REJECT", "msg": f"DEV demo trade failed: {type(e).__name__}"})
    finally:
        _state["running"] = False


@router.post("/run-demo-trade")
def run_demo_trade(req: DemoTrade | None = None) -> dict:
    if not enabled():   # belt and braces: the router is only mounted with NSQ_DEV=1
        raise HTTPException(404, "Not found")
    if _state["running"]:
        return {"state": "already running"}
    _state["running"] = True
    req = req or DemoTrade()
    threading.Thread(target=_run, args=(req,), daemon=True, name="dev-demo-trade").start()
    return {"state": "running", "strategy": DEV_SID, "synthetic": True}


@router.get("/demo-trade")
def demo_trade_status() -> dict:
    return dict(_state)
