"""ALT-DATA LAB (8.6).

Crop Watch     Sentinel-2 L2A scenes from the Microsoft Planetary Computer STAC API
               (POST https://planetarycomputer.microsoft.com/api/stac/v1/search, no key for search).
               V1 uses each scene's `s2:vegetation_percentage` (from ESA's scene classification),
               rescaled to the cloud-free part of the scene, as a vegetation index: this month vs the
               same window a year ago. True pixel NDVI ((B08-B04)/(B08+B04)) needs the optional
               `rasterio` package and signed asset URLs; not enabled in V1.
               Sentinel-2 data: "Contains modified Copernicus Sentinel data [year]" (free, open licence).
               Plus frost/heat forecasts from Open-Meteo (the weather layer).
Oil Storage V1 EIA API v2 weekly US crude stocks excluding SPR (series WCESTUS1). Needs your own free
               EIA key (eia_api_key). Cached. EIA data is US public domain.
Car Counts     LOCKED premium placeholder (needs paid high-resolution imagery). Returns nothing.
"""
from __future__ import annotations

import json
import time
from datetime import date, timedelta

from nsq.data.util import Blocked, cache_dir, emit, http_json, http_post_json, log, secret

from .impact import evaluate
from .layers import CROP_BELTS, get_layer

PC_SEARCH = "https://planetarycomputer.microsoft.com/api/stac/v1/search"
EIA_URL = "https://api.eia.gov/v2/petroleum/stoc/wstk/data/"


def _veg_index(features: list[dict]) -> tuple[float | None, int]:
    vals = []
    for f in features:
        p = f.get("properties", {})
        cloud = p.get("eo:cloud_cover")
        veg = p.get("s2:vegetation_percentage")
        if cloud is None or veg is None or cloud >= 80:
            continue
        clear = max(1e-6, 100 - cloud - (p.get("s2:nodata_pixel_percentage") or 0))
        vals.append(min(100.0, veg / clear * 100))
    return (round(sum(vals) / len(vals), 2) if vals else None), len(vals)


def crop_watch(days: int = 30, today: date | None = None) -> list[dict]:
    today = today or date.today()
    out = []
    for belt, b in CROP_BELTS.items():
        res = {"belt": belt, "crop": b["crop"], "lat": b["lat"], "lon": b["lon"]}
        try:
            windows = {"now": (today - timedelta(days=days), today),
                       "last_year": (today - timedelta(days=365 + days), today - timedelta(days=365))}
            for k, (s, e) in windows.items():
                d = http_post_json(PC_SEARCH, {"collections": ["sentinel-2-l2a"], "bbox": b["bbox"],
                                               "datetime": f"{s.isoformat()}T00:00:00Z/{e.isoformat()}T23:59:59Z",
                                               "query": {"eo:cloud_cover": {"lt": 80}}, "limit": 100})
                res[k], res[f"{k}_scenes"] = _veg_index(d.get("features", []))
            res["synthetic"] = False
        except (Blocked, OSError, ValueError) as e:
            res.update(now=None, last_year=None, synthetic=False, note=f"unavailable: {type(e).__name__}")
        res["attribution"] = f"Contains modified Copernicus Sentinel data {today.year} · via Microsoft Planetary Computer"
        out.append(res)
    (cache_dir("godseye") / "crop_watch.json").write_text(json.dumps(out))
    evs = [{"kind": "ndvi", "belt": r["belt"], "crop": r["crop"], "value": r["now"], "baseline": r["last_year"]}
           for r in out if r.get("now") is not None and r.get("last_year")]
    weather = get_layer("weather")
    if not weather.get("synthetic"):
        evs += [{**f, "kind": "weather"} for f in weather.get("features", [])]
    impacts = evaluate(evs)
    emit("gods_eye_event", {"layer": "crop_watch", "count": len(out), "features": out, "synthetic": False,
                            "attribution": out[0]["attribution"] if out else "", "impacts": len(impacts)})
    log("SAVE", f"Crop Watch · {sum(1 for r in out if r.get('now') is not None)} of {len(out)} belts measured · {len(impacts)} alerts")
    return out


def oil_storage(weeks: int = 12) -> dict:
    cache = cache_dir("godseye") / "eia_wcestus1.json"
    key = secret("eia_api_key")
    if not key:
        cached = json.loads(cache.read_text()) if cache.exists() else None
        return {"ok": False, "note": "needs your own free EIA API key (eia_api_key)", "cached": cached}
    try:
        d = http_json(EIA_URL, {"api_key": key, "frequency": "weekly", "data[0]": "value", "facets[series][]": "WCESTUS1",
                                "sort[0][column]": "period", "sort[0][direction]": "desc", "length": weeks})
        rows = [{"period": r["period"], "value_kb": float(r["value"])} for r in d.get("response", {}).get("data", [])]
        cache.write_text(json.dumps({"rows": rows, "fetched_at": int(time.time())}))
    except (Blocked, OSError, ValueError, KeyError) as e:
        cached = json.loads(cache.read_text()) if cache.exists() else None
        return {"ok": False, "note": f"EIA unavailable ({type(e).__name__})", "cached": cached}
    if len(rows) >= 3:
        ch = [(rows[i]["value_kb"] - rows[i + 1]["value_kb"]) / 1000 for i in range(len(rows) - 1)]
        evaluate([{"kind": "oil_stocks", "id": rows[0]["period"], "change_mb": ch[0],
                   "avg_change_mb": sum(ch[1:]) / max(1, len(ch) - 1)}])
    out = {"ok": True, "series": "WCESTUS1", "unit": "thousand barrels", "rows": rows,
           "attribution": "Source: U.S. Energy Information Administration"}
    emit("gods_eye_event", {"layer": "oil_storage", "count": len(rows), "features": rows, "synthetic": False,
                            "attribution": out["attribution"]})
    return out


def car_counts() -> dict:
    return {"locked": True, "tier": "premium", "note": "Car Counts needs paid high-resolution imagery. Locked placeholder."}
