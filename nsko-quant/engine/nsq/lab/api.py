"""FastAPI router for the Lab and the Knowledge Base. Mount with `app.include_router(nsq.lab.api.router)`.

Long runs go to a background thread; progress arrives on the bus (variant_tested, backtest_done)."""
from __future__ import annotations

import json
import threading

import pandas as pd
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from nsq.data import candles

from . import kb, runner, seed, signals

router = APIRouter(tags=["lab"])
_jobs: dict[str, dict] = {}


class RunReq(BaseModel):
    recipe_id: str | None = None
    recipe: dict | None = None
    start: str | None = None
    end: str | None = None
    variants: int | None = None


@router.post("/lab/seed")
def seed_pack() -> dict:
    return {"recipes": seed.seed_pack(), "kb_added": kb.seed()}


@router.post("/lab/run")
def run(req: RunReq) -> dict:
    rec = req.recipe or (runner.load_recipe(req.recipe_id) if req.recipe_id else None)
    if not rec:
        raise HTTPException(404, "recipe not found")
    try:
        signals.generator_for(rec)
    except ValueError as e:
        raise HTTPException(400, str(e))
    job = rec.get("id") or rec.get("name", "job")
    _jobs[job] = {"state": "running"}

    def _go():
        try:
            s = runner.run_recipe(rec, req.start, req.end, n_variants=req.variants)
            s.pop("rows", None)
            _jobs[job] = {"state": "done", "summary": s}
        except Exception as e:  # report, never crash the engine
            _jobs[job] = {"state": "error", "error": f"{type(e).__name__}: {e}"}

    threading.Thread(target=_go, daemon=True, name=f"lab-{job}").start()
    return {"job": job, "state": "running"}


@router.get("/lab/jobs")
def jobs() -> dict:
    return _jobs


@router.get("/lab/recipes")
def recipes() -> dict:
    runner.ensure()
    from nsq.db import conn
    rows = conn().execute("SELECT id, name, market, timeframe, idea_type, status, origin, created_at FROM recipes ORDER BY created_at DESC").fetchall()
    return {"recipes": rows}


@router.get("/lab/variants")
def variants(recipe_id: str | None = None, limit: int = 200) -> dict:
    runner.ensure()
    from nsq.db import conn
    q = "SELECT * FROM variants" + (" WHERE recipe_id=?" if recipe_id else "") + " ORDER BY id DESC LIMIT ?"
    rows = conn().execute(q, ((recipe_id, limit) if recipe_id else (limit,))).fetchall()
    return {"variants": rows}


@router.get("/lab/backtests/{variant_id}")
def backtest(variant_id: int) -> dict:
    runner.ensure()
    from nsq.db import conn
    r = conn().execute("SELECT * FROM backtests WHERE variant_id=?", (variant_id,)).fetchone()
    if not r:
        raise HTTPException(404, "no backtest")
    for k in ("split_json", "costs_json", "metrics_is", "metrics_oos", "chance_json", "mc_json", "stability_json", "equity_json"):
        r[k] = json.loads(r[k]) if r[k] else None
    return r


@router.get("/lab/fan")
def fan(recipe_id: str) -> dict:
    """Every variant's downsampled equity curve for the Lab fan chart."""
    runner.ensure()
    from nsq.db import conn
    rows = conn().execute("SELECT v.id, v.label, v.outcome, b.equity_json FROM variants v JOIN backtests b ON b.variant_id=v.id"
                          " WHERE v.recipe_id=? ORDER BY v.id", (recipe_id,)).fetchall()
    return {"lines": [{"id": r["id"], "label": r["label"], "outcome": r["outcome"], "equity": json.loads(r["equity_json"])} for r in rows]}


@router.get("/lab/signals")
def preview_signals(recipe_id: str, bars: int = 2000) -> dict:
    rec = runner.load_recipe(recipe_id)
    if not rec:
        raise HTTPException(404, "recipe not found")
    df = candles.latest(rec["market"], rec["timeframe"], bars)
    return {"synthetic": bool(df.attrs.get("synthetic")), "signals": signals.generate(rec, df)[-50:]}


@router.get("/kb")
def kb_all() -> dict:
    kb.seed()
    return {"concepts": kb.all_concepts(), "lifecycle": kb.LIFECYCLE}


@router.get("/kb/{slug}")
def kb_one(slug: str) -> dict:
    c = kb.get(slug)
    if not c:
        raise HTTPException(404, "unknown concept")
    return c


@router.post("/kb/measure")
def kb_measure(market: str = "XAU/USD", tf: str = "15m", days: int = 180) -> dict:
    kb.seed()
    end = pd.Timestamp.now(tz="UTC")
    df = candles.get(market, tf, end - pd.Timedelta(days=days), end)
    return kb.measure(df)


class Verdict(BaseModel):
    verdict: str


@router.post("/kb/{slug}/verdict")
def kb_verdict(slug: str, v: Verdict) -> dict:
    try:
        return kb.set_verdict(slug, v.verdict)
    except ValueError as e:
        raise HTTPException(400, str(e))
