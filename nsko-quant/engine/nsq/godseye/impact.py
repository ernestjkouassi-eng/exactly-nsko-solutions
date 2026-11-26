"""MARKET IMPACT rules engine (8.6).

event -> asset -> JARVIS note -> optional risk action (cut size / pause new trades).
It NEVER opens a trade: this module has no access to brokers or the order flow, and every
`market_impact` payload carries `opens_trade: False`. Risk actions are suggestions unless the
user sets godseye.risk_actions = "apply"; applied actions are written to `godseye_risk_flags`,
which the risk gate can read with `active_risk_flags()` (they only ever reduce risk).

Input events are plain dicts (built from the layers by `events_from_layers`, or synthetic in tests):
  {"kind": "chokepoint_speed", "chokepoint", "tanker_avg_kn", "baseline_kn", "n"}
  {"kind": "mil_flights", "region", "count", "baseline"}
  {"kind": "quake", "mag", "lat", "lon", "place", "id"}
  {"kind": "weather", "belt", "crop", "tmin", "tmax", "precip_sum", "days"}
  {"kind": "ndvi", "belt", "crop", "value", "baseline"}
  {"kind": "fires", "belt", "count", "baseline"}
  {"kind": "oil_stocks", "change_mb", "avg_change_mb"}
"""
from __future__ import annotations

import math
import time
import zlib
from dataclasses import dataclass
from typing import Callable

from nsq.data.util import emit, ensure_table, jdump, log, now_ms, setting

from .layers import CHOKEPOINTS, MIL_REGIONS

DEFAULTS = {"godseye.risk_actions": "suggest",   # suggest | apply
            "godseye.quake_min_mag": 6.0, "godseye.quake_radius_km": 150.0,
            "godseye.tanker_slowdown_pct": 30.0, "godseye.mil_surge_x": 1.5, "godseye.flag_hours": 24}

# Mines and ports that matter for metals (approximate coordinates)
SITES = [
    {"name": "Escondida copper mine, Chile", "lat": -24.27, "lon": -69.07, "assets": ["COPPER"]},
    {"name": "Collahuasi copper mine, Chile", "lat": -20.98, "lon": -68.64, "assets": ["COPPER"]},
    {"name": "Antofagasta port, Chile", "lat": -23.65, "lon": -70.40, "assets": ["COPPER"]},
    {"name": "Grasberg mine, Indonesia", "lat": -4.05, "lon": 137.11, "assets": ["COPPER", "XAU/USD"]},
    {"name": "Kolwezi copper-cobalt belt, DR Congo", "lat": -10.72, "lon": 25.47, "assets": ["COPPER", "COBALT"]},
    {"name": "Witwatersrand gold fields, South Africa", "lat": -26.40, "lon": 27.70, "assets": ["XAU/USD", "PLATINUM"]},
    {"name": "Bushveld platinum complex, South Africa", "lat": -25.00, "lon": 28.00, "assets": ["PLATINUM", "PALLADIUM"]},
    {"name": "Port Hedland, Australia", "lat": -20.31, "lon": 118.58, "assets": ["IRON ORE"]},
    {"name": "Callao port, Peru", "lat": -12.05, "lon": -77.15, "assets": ["COPPER", "ZINC", "XAG/USD"]},
    {"name": "Muruntau gold mine, Uzbekistan", "lat": 41.50, "lon": 64.60, "assets": ["XAU/USD"]},
]


def haversine_km(a_lat, a_lon, b_lat, b_lon) -> float:
    p1, p2 = math.radians(a_lat), math.radians(b_lat)
    dp, dl = p2 - p1, math.radians(b_lon - a_lon)
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * 6371.0 * math.asin(math.sqrt(h))


@dataclass
class Rule:
    id: str
    kind: str
    check: Callable[[dict], dict | None]   # returns {assets, note, risk_action, severity} or None


def _cfg(k):
    return setting(k, DEFAULTS)


def _r_tanker(ev):
    base, now = ev.get("baseline_kn"), ev.get("tanker_avg_kn")
    if not base or now is None or ev.get("n", 0) < 3:
        return None
    drop = (base - now) / base * 100
    if drop < float(_cfg("godseye.tanker_slowdown_pct")):
        return None
    sev = "high" if drop >= 50 else "medium"
    return {"assets": ["WTI", "BRENT", "XAU/USD"], "severity": sev, "risk_action": "cut_size" if sev == "high" else None,
            "note": f"Tankers at {ev['chokepoint']} are moving {drop:.0f}% slower than usual ({now:.1f} vs {base:.1f} knots, "
                    f"{ev['n']} ships). Oil supply risk; gold often catches a safe-haven bid. Watch, don't chase."}


def _r_mil(ev):
    base, c = ev.get("baseline"), ev.get("count", 0)
    if not base or c < 5:
        return None
    x = c / base
    if x < float(_cfg("godseye.mil_surge_x")):
        return None
    sev = "high" if x >= 2.5 else "medium"
    return {"assets": ["XAU/USD", "USD/JPY", "USD/CHF"], "severity": sev, "risk_action": "pause_new" if sev == "high" else "cut_size",
            "note": f"Military flights over {ev['region']} are {x:.1f}x normal ({c} vs ~{base:.0f}). "
                    "Safe-haven watch: gold, yen and franc can jump on headlines."}


def _r_quake(ev):
    if (ev.get("mag") or 0) < float(_cfg("godseye.quake_min_mag")):
        return None
    radius = float(_cfg("godseye.quake_radius_km"))
    near = [(s, haversine_km(ev["lat"], ev["lon"], s["lat"], s["lon"])) for s in SITES]
    near = [(s, d) for s, d in near if d <= radius]
    if not near:
        return None
    s, d = min(near, key=lambda x: x[1])
    assets = sorted({a for s2, _ in near for a in s2["assets"]})
    sev = "high" if ev["mag"] >= 7 else "medium"
    return {"assets": assets, "severity": sev, "risk_action": "cut_size" if sev == "high" and "XAU/USD" in assets else None,
            "note": f"M{ev['mag']:.1f} earthquake {d:.0f} km from {s['name']}. Possible supply disruption for "
                    f"{', '.join(assets)}; first reports are often wrong, so wait for damage news."}


CROP_ASSET = {"coffee": "COFFEE", "cocoa": "COCOA", "wheat": "WHEAT", "corn": "CORN"}


def _r_weather(ev):
    crop, tmin, tmax, rain = ev.get("crop"), ev.get("tmin"), ev.get("tmax"), ev.get("precip_sum")
    asset = CROP_ASSET.get(crop)
    if not asset:
        return None
    hits = []
    if crop == "coffee" and tmin is not None and tmin <= 2.0:
        hits.append(f"frost risk ({tmin:.1f} °C forecast low)")
    if crop == "wheat" and tmin is not None and tmin <= -10.0:
        hits.append(f"hard freeze ({tmin:.1f} °C)")
    if crop in ("cocoa", "corn", "wheat") and tmax is not None and tmax >= 36.0:
        hits.append(f"heat stress ({tmax:.1f} °C forecast high)")
    if rain is not None and ev.get("days", 7) >= 7 and rain < {"cocoa": 5.0, "coffee": 3.0}.get(crop, 2.0):
        hits.append(f"dry week ({rain:.1f} mm in {ev.get('days', 7)} days)")
    if not hits:
        return None
    return {"assets": [asset], "severity": "medium", "risk_action": None,
            "note": f"{ev['belt']}: {', '.join(hits)}. {asset.title()} prices can react to crop weather; "
                    "context only, check the season before reading much into it."}


def _r_ndvi(ev):
    v, b = ev.get("value"), ev.get("baseline")
    if v is None or not b:
        return None
    drop = (b - v) / b * 100
    if drop < 15:
        return None
    asset = CROP_ASSET.get(ev.get("crop"), "SOFTS")
    return {"assets": [asset], "severity": "medium", "risk_action": None,
            "note": f"{ev['belt']}: vegetation is {drop:.0f}% below the same time last year (Sentinel-2). "
                    f"Possible weaker {ev.get('crop')} crop; slow signal, context only."}


def _r_fires(ev):
    c, b = ev.get("count", 0), ev.get("baseline") or 0
    if c < 50 or (b and c < 2 * b):
        return None
    asset = CROP_ASSET.get(ev.get("crop"), "SOFTS")
    return {"assets": [asset], "severity": "low", "risk_action": None,
            "note": f"{c} fire detections around {ev['belt']} (normal ~{b:.0f}). Often field burning; context only."}


def _r_oil(ev):
    ch, avg = ev.get("change_mb"), ev.get("avg_change_mb", 0.0)
    if ch is None or abs(ch - avg) < 5.0:
        return None
    up = ch > avg
    return {"assets": ["WTI", "BRENT"], "severity": "low", "risk_action": None,
            "note": f"US crude stocks {'rose' if ch > 0 else 'fell'} {abs(ch):.1f} million barrels (typical {avg:+.1f}). "
                    f"{'Bearish' if up else 'Bullish'} for oil on the day; the market often prices it in minutes."}


RULES = [Rule("tanker_slowdown", "chokepoint_speed", _r_tanker), Rule("military_surge", "mil_flights", _r_mil),
         Rule("quake_near_site", "quake", _r_quake), Rule("crop_weather", "weather", _r_weather),
         Rule("crop_ndvi", "ndvi", _r_ndvi), Rule("crop_fires", "fires", _r_fires), Rule("oil_stocks", "oil_stocks", _r_oil)]


def ensure() -> None:
    from nsq.db import conn
    c = conn()
    ensure_table(c, "godseye_impacts", {"id": "TEXT PRIMARY KEY", "rule": "TEXT", "event_json": "TEXT", "assets": "TEXT",
                                        "note": "TEXT", "risk_action": "TEXT", "applied": "INTEGER", "severity": "TEXT",
                                        "synthetic": "INTEGER", "created_at": "INTEGER"})
    ensure_table(c, "godseye_risk_flags", {"id": "INTEGER PRIMARY KEY AUTOINCREMENT", "impact_id": "TEXT", "asset": "TEXT",
                                           "action": "TEXT", "expires_at": "INTEGER", "created_at": "INTEGER"})
    ensure_table(c, "godseye_baselines", {"key": "TEXT PRIMARY KEY", "value": "REAL", "n": "INTEGER", "updated_at": "INTEGER"})


def evaluate(events: list[dict], store: bool = True, publish: bool = True) -> list[dict]:
    """Run every rule over every event. Returns the market_impact payloads (deduplicated per day)."""
    out = []
    mode = _cfg("godseye.risk_actions")
    if store:
        ensure()
    for ev in events:
        for rule in RULES:
            if rule.kind != ev.get("kind"):
                continue
            hit = rule.check(ev)
            if not hit:
                continue
            day = time.strftime("%Y-%m-%d", time.gmtime())
            key = ev.get("id") or ev.get("chokepoint") or ev.get("region") or ev.get("belt") or ""
            iid = f"{rule.id}:{key}:{day}:{zlib.crc32(jdump(hit['assets']).encode()):x}"
            applied = bool(hit["risk_action"]) and mode == "apply"
            payload = {"id": iid, "rule": rule.id, "event": {k: v for k, v in ev.items() if k != "daily"},
                       "asset": hit["assets"][0], "assets": hit["assets"], "note": hit["note"], "jarvis": hit["note"],
                       "risk_action": hit["risk_action"], "risk_action_applied": applied, "severity": hit["severity"],
                       "opens_trade": False, "synthetic": bool(ev.get("synthetic")), "ts": now_ms()}
            if store:
                from nsq.db import conn
                c = conn()
                cur = c.execute("INSERT OR IGNORE INTO godseye_impacts (id, rule, event_json, assets, note, risk_action, applied, severity,"
                                " synthetic, created_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
                                (iid, rule.id, jdump(payload["event"]), jdump(hit["assets"]), hit["note"], hit["risk_action"],
                                 int(applied), hit["severity"], int(payload["synthetic"]), now_ms()))
                if not cur.rowcount:
                    continue            # already raised today
                if applied:
                    exp = now_ms() + int(float(_cfg("godseye.flag_hours")) * 3600 * 1000)
                    for a in hit["assets"]:
                        c.execute("INSERT INTO godseye_risk_flags (impact_id, asset, action, expires_at, created_at) VALUES (?,?,?,?,?)",
                                  (iid, a, hit["risk_action"], exp, now_ms()))
            if publish:
                emit("market_impact", payload)
                log("RISK", f"God's Eye · {hit['note'][:110]}" + (f" · {hit['risk_action']}" + (" applied" if applied else " suggested")
                                                                 if hit["risk_action"] else ""))
            out.append(payload)
    return out


def active_risk_flags(asset: str | None = None) -> list[dict]:
    """Unexpired risk-reducing flags (cut_size / pause_new) for the risk gate to honour."""
    ensure()
    from nsq.db import conn
    q = "SELECT asset, action, impact_id, expires_at FROM godseye_risk_flags WHERE expires_at > ?"
    args: tuple = (now_ms(),)
    if asset:
        q += " AND asset = ?"
        args += (asset,)
    return conn().execute(q, args).fetchall()


# --------------------------------------------------------------------------- layer -> events

def _baseline(key: str, value: float, alpha: float = 0.1) -> float | None:
    """Exponential moving baseline, stored; returns the baseline BEFORE this observation."""
    ensure()
    from nsq.db import conn
    c = conn()
    r = c.execute("SELECT value, n FROM godseye_baselines WHERE key=?", (key,)).fetchone()
    prev = r["value"] if r else None
    new = value if prev is None else (1 - alpha) * prev + alpha * value
    c.execute("INSERT INTO godseye_baselines (key, value, n, updated_at) VALUES (?,?,1,?) ON CONFLICT(key) DO UPDATE SET "
              "value=excluded.value, n=n+1, updated_at=excluded.updated_at", (key, new, now_ms()))
    return prev if (r and r["n"] >= 3) else None


def events_from_layers(layers: dict[str, dict]) -> list[dict]:
    evs: list[dict] = []
    fl = layers.get("flights")
    if fl and fl.get("features") and not fl.get("synthetic"):
        for name, b in MIL_REGIONS.items():
            n = sum(1 for f in fl["features"] if b[0] <= (f.get("lat") or -999) <= b[1] and b[2] <= (f.get("lon") or -999) <= b[3])
            evs.append({"kind": "mil_flights", "region": name, "count": n, "baseline": _baseline(f"mil:{name}", n)})
    sh = layers.get("ships")
    if sh and sh.get("features") and not sh.get("synthetic"):
        for name, b in CHOKEPOINTS.items():
            sp = [f["sog"] for f in sh["features"] if f.get("tanker") and f.get("sog") is not None
                  and b[0] <= f["lat"] <= b[1] and b[2] <= f["lon"] <= b[3]]
            if sp:
                avg = sum(sp) / len(sp)
                evs.append({"kind": "chokepoint_speed", "chokepoint": name, "tanker_avg_kn": avg, "n": len(sp),
                            "baseline_kn": _baseline(f"tank:{name}", avg)})
    q = layers.get("quakes")
    if q and not q.get("synthetic"):   # never raise impacts from made-up data
        evs += [{"kind": "quake", **{k: f.get(k) for k in ("id", "mag", "lat", "lon", "place")}, "synthetic": q.get("synthetic", False)}
                for f in q.get("features", []) if f.get("mag") is not None]
    w = layers.get("weather")
    if w and not w.get("synthetic"):
        evs += [{**f, "kind": "weather", "synthetic": w.get("synthetic", False)} for f in w.get("features", [])]
    fi = layers.get("fires")
    if fi and fi.get("features") and not fi.get("synthetic"):
        from .layers import CROP_BELTS
        for belt, b in CROP_BELTS.items():
            n = sum(1 for f in fi["features"] if f.get("belt") == belt)
            evs.append({"kind": "fires", "belt": belt, "crop": b["crop"], "count": n, "baseline": _baseline(f"fire:{belt}", n)})
    return evs


def scan() -> dict:
    """Refresh the enabled layers, derive events, run the rules."""
    from .layers import FETCHERS, enabled, get_layer
    layers = {name: get_layer(name) for name in FETCHERS if enabled(name)}
    evs = events_from_layers(layers)
    impacts = evaluate(evs)
    return {"layers": {k: {"count": len(v.get("features", [])), "synthetic": v.get("synthetic"), "cached": v.get("cached"),
                           "note": v.get("note")} for k, v in layers.items()}, "events": len(evs), "impacts": impacts}
