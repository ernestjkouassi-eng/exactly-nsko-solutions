"""FastAPI router for the JARVIS research team. Mount with `app.include_router(nsq.research.api.router)`."""
from __future__ import annotations

import threading

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from . import llm, pipeline

router = APIRouter(prefix="/research", tags=["research"])
_state = {"running": False, "last": None}


class RoundReq(BaseModel):
    queries: list[str] | None = None
    kinds: list[str] | None = None
    max_sources: int | None = None


@router.post("/round")
def start_round(req: RoundReq) -> dict:
    if _state["running"]:
        return {"state": "already running"}
    _state["running"] = True

    def _go():
        try:
            _state["last"] = pipeline.run_round(req.queries, req.kinds, req.max_sources)
        except Exception as e:
            _state["last"] = {"error": f"{type(e).__name__}: {e}"}
        finally:
            _state["running"] = False

    threading.Thread(target=_go, daemon=True, name="research-round").start()
    return {"state": "running", "mode": llm.mode()}


@router.get("/status")
def status() -> dict:
    return {**_state, "mode": llm.mode(), "budget": pipeline.Budget().emit(), "agents": pipeline.AGENTS}


@router.get("/{table}")
def table(table: str, limit: int = 100) -> dict:
    try:
        return {table: pipeline.listing(table, limit)}
    except ValueError:
        raise HTTPException(404, "unknown table")
