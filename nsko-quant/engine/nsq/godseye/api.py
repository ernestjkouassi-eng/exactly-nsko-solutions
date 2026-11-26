"""FastAPI router for God's Eye. Mount with `app.include_router(nsq.godseye.api.router)`."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from nsq.data.util import setting

from . import altdata, impact, layers

router = APIRouter(prefix="/godseye", tags=["godseye"])


@router.get("/layers")
def all_layers() -> dict:
    return {"layers": [{"layer": k, "enabled": layers.enabled(k), "attribution": layers.ATTRIBUTION[k]} for k in layers.FETCHERS],
            "risk_actions": setting("godseye.risk_actions", impact.DEFAULTS)}


@router.get("/layer/{name}")
def one_layer(name: str, refresh: bool = True) -> dict:
    if name not in layers.FETCHERS:
        raise HTTPException(404, "unknown layer")
    return layers.get_layer(name, refresh)


@router.post("/scan")
def scan() -> dict:
    return impact.scan()


@router.get("/impacts")
def impacts(limit: int = 100) -> dict:
    impact.ensure()
    from nsq.db import conn
    return {"impacts": conn().execute("SELECT * FROM godseye_impacts ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall(),
            "active_flags": impact.active_risk_flags()}


@router.post("/altdata/crop-watch")
def crop_watch() -> dict:
    return {"belts": altdata.crop_watch()}


@router.get("/altdata/oil-storage")
def oil_storage() -> dict:
    return altdata.oil_storage()


@router.get("/altdata/car-counts")
def car_counts() -> dict:
    return altdata.car_counts()
