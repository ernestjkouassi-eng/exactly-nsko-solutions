"""God's Eye free layers (8.6). Each layer has an attribution line and an on/off flag in settings
(`godseye.layer.<name>.enabled`). A layer that cannot reach its host returns its last cached copy,
and with no cache a small seeded synthetic set flagged `synthetic=True` (so the globe never lies).

  flights     adsb.lol API v2 (/v2/mil, /v2/point/{lat}/{lon}/{radius_nm}); data ODbL 1.0, no key
  ships       AISStream.io WebSocket; BRING YOUR OWN free key (aisstream_api_key); off by default
  satellites  CelesTrak GP data (gp.php?GROUP=&FORMAT=json); fetch at most every 2 hours
  quakes      USGS earthquake GeoJSON summary feeds; US public domain
  fires       NASA FIRMS area API; BRING YOUR OWN free MAP_KEY (firms_map_key); off by default
  weather     Open-Meteo forecast API (optionally the NOAA GFS model via models=gfs_seamless);
              CC BY 4.0; the free API is for non-commercial use (commercial: own Open-Meteo key)
  launches    Launch Library 2 (The Space Devs); free tier 15 requests/hour

Not used, by rule: OpenSky, Cesium ion, Google 3D Tiles, CCTV feeds, TeleGeography cables.
"""
from __future__ import annotations

import asyncio
import csv
import io
import json
import math
import time
import zlib

import numpy as np

from nsq.data.util import Blocked, cache_dir, emit, http_get, http_json, secret, setting

ATTRIBUTION = {
    "flights": "Flight data: adsb.lol contributors, ODbL 1.0",
    "ships": "AIS data: aisstream.io (your own key)",
    "satellites": "Orbital elements: CelesTrak (Dr T.S. Kelso)",
    "quakes": "Earthquakes: U.S. Geological Survey (public domain)",
    "fires": "Fires: NASA FIRMS (LANCE / EOSDIS), your own MAP_KEY",
    "weather": "Weather: Open-Meteo.com (CC BY 4.0), models incl. NOAA GFS",
    "launches": "Launches: Launch Library 2 by The Space Devs",
}
DEFAULTS = {
    "godseye.layer.flights.enabled": True, "godseye.layer.ships.enabled": False, "godseye.layer.satellites.enabled": True,
    "godseye.layer.quakes.enabled": True, "godseye.layer.fires.enabled": False, "godseye.layer.weather.enabled": True,
    "godseye.layer.launches.enabled": True,
    "godseye.quake_feed": "4.5_day", "godseye.celestrak_groups": ["stations", "weather"],
    "godseye.weather_model": "best_match",      # or gfs_seamless (NOAA GFS through Open-Meteo)
    "godseye.ais_listen_s": 20,
}

# Chokepoints (lat_min, lat_max, lon_min, lon_max)
CHOKEPOINTS = {
    "Hormuz": (25.5, 27.2, 55.5, 57.5),
    "Bab-el-Mandeb / Red Sea": (12.0, 14.5, 42.5, 44.5),
    "Suez": (29.8, 31.4, 32.2, 32.7),
}
MIL_REGIONS = {
    "Gulf": (22.0, 32.0, 46.0, 60.0), "Eastern Europe / Black Sea": (42.0, 56.0, 22.0, 42.0),
    "Taiwan Strait": (20.0, 27.0, 116.0, 124.0), "Korean Peninsula": (33.0, 43.0, 124.0, 131.0),
    "Eastern Mediterranean": (31.0, 37.0, 28.0, 36.5),
}
CROP_BELTS = {
    "Minas Gerais coffee": {"lat": -21.0, "lon": -45.5, "crop": "coffee", "bbox": [-46.5, -22.0, -44.5, -20.0]},
    "Cote d'Ivoire cocoa": {"lat": 6.8, "lon": -5.3, "crop": "cocoa", "bbox": [-6.5, 5.8, -4.0, 7.8]},
    "Ghana cocoa": {"lat": 6.7, "lon": -1.6, "crop": "cocoa", "bbox": [-2.8, 5.8, -0.5, 7.5]},
    "Kansas wheat": {"lat": 38.5, "lon": -98.5, "crop": "wheat", "bbox": [-100.5, 37.5, -96.5, 39.5]},
    "Ukraine wheat": {"lat": 48.5, "lon": 35.0, "crop": "wheat", "bbox": [33.5, 47.5, 36.5, 49.5]},
    "Iowa corn": {"lat": 42.0, "lon": -93.5, "crop": "corn", "bbox": [-95.0, 41.0, -92.0, 43.0]},
}


def enabled(layer: str) -> bool:
    return bool(setting(f"godseye.layer.{layer}.enabled", DEFAULTS))


def _cache_write(layer: str, data: dict) -> None:
    (cache_dir("godseye") / f"{layer}.json").write_text(json.dumps(data, default=str))


def _cache_read(layer: str) -> dict | None:
    p = cache_dir("godseye") / f"{layer}.json"
    return json.loads(p.read_text()) if p.exists() else None


def _in(b, lat, lon) -> bool:
    return lat is not None and lon is not None and b[0] <= lat <= b[1] and b[2] <= lon <= b[3]


# ----------------------------------------------------------------------------------- fetchers

def fetch_flights() -> list[dict]:
    d = http_json("https://api.adsb.lol/v2/mil")
    return [{"id": a.get("hex"), "lat": a["lat"], "lon": a["lon"], "kind": "military aircraft",
             "callsign": (a.get("flight") or "").strip(), "type": a.get("t"), "alt": a.get("alt_baro"), "gs": a.get("gs")}
            for a in d.get("ac", []) if a.get("lat") is not None]


async def _ais(key: str, seconds: int) -> list[dict]:
    import websockets
    boxes = [[[b[0], b[2]], [b[1], b[3]]] for b in CHOKEPOINTS.values()]
    ships: dict = {}
    static: dict = {}
    async with websockets.connect("wss://stream.aisstream.io/v0/stream", open_timeout=15) as ws:
        await ws.send(json.dumps({"APIKey": key, "BoundingBoxes": boxes,
                                  "FilterMessageTypes": ["PositionReport", "ShipStaticData"]}))
        t0 = time.time()
        while time.time() - t0 < seconds:
            try:
                m = json.loads(await asyncio.wait_for(ws.recv(), timeout=max(1, seconds - (time.time() - t0))))
            except asyncio.TimeoutError:
                break
            meta = m.get("MetaData", {})
            mmsi = meta.get("MMSI")
            if m.get("MessageType") == "ShipStaticData":
                static[mmsi] = m["Message"]["ShipStaticData"].get("Type")
            elif m.get("MessageType") == "PositionReport":
                pr = m["Message"]["PositionReport"]
                ships[mmsi] = {"id": mmsi, "lat": pr.get("Latitude"), "lon": pr.get("Longitude"), "sog": pr.get("Sog"),
                               "name": (meta.get("ShipName") or "").strip(), "kind": "vessel"}
    for k, s in ships.items():
        t = static.get(k)
        s["ship_type"] = t
        s["tanker"] = bool(t and 80 <= int(t) <= 89)
    return list(ships.values())


def fetch_ships() -> list[dict]:
    key = secret("aisstream_api_key")
    if not key:
        raise PermissionError("ships need your own free AISStream key (aisstream_api_key)")
    return asyncio.run(_ais(key, int(setting("godseye.ais_listen_s", DEFAULTS))))


def fetch_satellites() -> list[dict]:
    out = []
    for g in setting("godseye.celestrak_groups", DEFAULTS):
        rows = http_json("https://celestrak.org/NORAD/elements/gp.php", {"GROUP": g, "FORMAT": "json"}, timeout=30)
        for r in rows:
            f = {"id": r.get("NORAD_CAT_ID"), "name": r.get("OBJECT_NAME"), "group": g, "kind": "satellite",
                 "epoch": r.get("EPOCH"), "mean_motion": r.get("MEAN_MOTION"), "inclination": r.get("INCLINATION")}
            f.update(_subpoint(r))
            out.append(f)
    return out


def _subpoint(gp: dict) -> dict:
    """Current sub-satellite point if the optional `sgp4` package (MIT) is installed."""
    try:
        from sgp4.api import Satrec, jday
        from sgp4 import omm
    except ImportError:
        return {"lat": None, "lon": None}
    try:
        sat = Satrec()
        omm.initialize(sat, gp)
        t = time.gmtime()
        jd, fr = jday(t.tm_year, t.tm_mon, t.tm_mday, t.tm_hour, t.tm_min, t.tm_sec)
        e, r, _ = sat.sgp4(jd, fr)
        if e:
            return {"lat": None, "lon": None}
        x, y, z = r
        gmst = (280.46061837 + 360.98564736629 * (jd + fr - 2451545.0)) % 360
        lon = (math.degrees(math.atan2(y, x)) - gmst + 540) % 360 - 180
        lat = math.degrees(math.atan2(z, math.hypot(x, y)))
        return {"lat": round(lat, 3), "lon": round(lon, 3)}
    except Exception:
        return {"lat": None, "lon": None}


def fetch_quakes() -> list[dict]:
    feed = setting("godseye.quake_feed", DEFAULTS)
    d = http_json(f"https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/{feed}.geojson")
    return [{"id": f["id"], "lon": f["geometry"]["coordinates"][0], "lat": f["geometry"]["coordinates"][1],
             "depth_km": f["geometry"]["coordinates"][2], "mag": f["properties"].get("mag"), "kind": "earthquake",
             "place": f["properties"].get("place"), "time": f["properties"].get("time"), "url": f["properties"].get("url")}
            for f in d.get("features", [])]


def fetch_fires(days: int = 2) -> list[dict]:
    key = secret("firms_map_key")
    if not key:
        raise PermissionError("fires need your own free NASA FIRMS MAP_KEY (firms_map_key)")
    out = []
    for name, b in CROP_BELTS.items():
        w, s, e, n = b["bbox"]
        raw = http_get(f"https://firms.modaps.eosdis.nasa.gov/api/area/csv/{key}/VIIRS_SNPP_NRT/{w},{s},{e},{n}/{days}")
        for row in csv.DictReader(io.StringIO(raw.decode("utf-8", "replace"))):
            out.append({"id": f"{row.get('latitude')},{row.get('longitude')},{row.get('acq_date')}", "kind": "fire",
                        "lat": float(row["latitude"]), "lon": float(row["longitude"]), "belt": name,
                        "frp": float(row.get("frp") or 0), "date": row.get("acq_date")})
    return out


def fetch_weather(days: int = 7) -> list[dict]:
    model = setting("godseye.weather_model", DEFAULTS)
    out = []
    for name, b in CROP_BELTS.items():
        p = {"latitude": b["lat"], "longitude": b["lon"], "daily": "temperature_2m_min,temperature_2m_max,precipitation_sum",
             "forecast_days": days, "timezone": "UTC"}
        if model and model != "best_match":
            p["models"] = model
        key = secret("open_meteo_api_key")
        url = "https://api.open-meteo.com/v1/forecast"
        if key:   # commercial use: customer API with your own key
            url, p["apikey"] = "https://customer-api.open-meteo.com/v1/forecast", key
        d = http_json(url, p)["daily"]
        out.append({"id": name, "kind": "weather", "lat": b["lat"], "lon": b["lon"], "belt": name, "crop": b["crop"],
                    "tmin": min(x for x in d["temperature_2m_min"] if x is not None),
                    "tmax": max(x for x in d["temperature_2m_max"] if x is not None),
                    "precip_sum": round(sum(x or 0 for x in d["precipitation_sum"]), 1), "days": days, "daily": d})
    return out


def fetch_launches(n: int = 10) -> list[dict]:
    d = http_json("https://ll.thespacedevs.com/2.2.0/launch/upcoming/", {"limit": n})
    out = []
    for r in d.get("results", []):
        pad = r.get("pad") or {}
        out.append({"id": r["id"], "kind": "launch", "name": r.get("name"), "net": r.get("net"),
                    "status": (r.get("status") or {}).get("name"),
                    "lat": float(pad["latitude"]) if pad.get("latitude") else None,
                    "lon": float(pad["longitude"]) if pad.get("longitude") else None,
                    "site": (pad.get("location") or {}).get("name")})
    return out


FETCHERS = {"flights": fetch_flights, "ships": fetch_ships, "satellites": fetch_satellites, "quakes": fetch_quakes,
            "fires": fetch_fires, "weather": fetch_weather, "launches": fetch_launches}


# ---------------------------------------------------------------------------------- synthetic

def synthetic(layer: str, n: int = 12) -> list[dict]:
    rng = np.random.default_rng(zlib.crc32(layer.encode()))
    feats = []
    for i in range(n):
        lat, lon = float(rng.uniform(-50, 60)), float(rng.uniform(-170, 170))
        f = {"id": f"syn-{layer}-{i}", "lat": round(lat, 3), "lon": round(lon, 3), "kind": layer, "synthetic": True}
        if layer == "quakes":
            f.update(mag=round(float(rng.uniform(4.5, 6.5)), 1), place="synthetic quake", depth_km=10.0)
        if layer == "weather":
            name = list(CROP_BELTS)[i % len(CROP_BELTS)]
            b = CROP_BELTS[name]
            f.update(id=name, lat=b["lat"], lon=b["lon"], belt=name, crop=b["crop"], tmin=15.0, tmax=28.0, precip_sum=20.0, days=7)
        feats.append(f)
    return feats[: len(CROP_BELTS)] if layer == "weather" else feats


def get_layer(layer: str, refresh: bool = True) -> dict:
    """Layer features + attribution + provenance flags. Emits a `gods_eye_event` summary."""
    if layer not in FETCHERS:
        raise KeyError(layer)
    base = {"layer": layer, "attribution": ATTRIBUTION[layer], "enabled": enabled(layer)}
    if not base["enabled"]:
        return {**base, "features": [], "synthetic": False, "cached": False, "note": "layer is off in settings"}
    note = None
    if refresh:
        try:
            feats = FETCHERS[layer]()
            data = {**base, "features": feats, "synthetic": False, "cached": False, "fetched_at": int(time.time())}
            _cache_write(layer, data)
            _emit(data)
            return data
        except (Blocked, PermissionError, OSError, ValueError, KeyError, RuntimeError) as e:
            note = f"{type(e).__name__}: {str(e)[:160]}"
        except Exception as e:  # malformed upstream response, etc.
            note = f"{type(e).__name__}: {str(e)[:160]}"
    cached = _cache_read(layer)
    if cached:
        data = {**cached, "cached": True, "note": note}
    else:
        data = {**base, "features": synthetic(layer), "synthetic": True, "cached": False, "note": note}
    _emit(data)
    return data


def _emit(data: dict) -> None:
    emit("gods_eye_event", {"layer": data["layer"], "count": len(data.get("features", [])), "attribution": data["attribution"],
                            "synthetic": data.get("synthetic", False), "cached": data.get("cached", False),
                            "features": data.get("features", [])[:500], "note": data.get("note")})
