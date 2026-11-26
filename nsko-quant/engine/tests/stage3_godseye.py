"""MARKET IMPACT rules on synthetic test events; layers degrade to cache/synthetic offline."""
import sys

import pytest

import stage3_helpers as h
from nsq.godseye import altdata, impact, layers


def _run(events, **kw):
    rec = h.Recorder()
    out = impact.evaluate(events, **kw)
    rec.close()
    return out, rec


def test_tanker_slowdown_at_hormuz_maps_to_oil_and_gold():
    out, rec = _run([{"kind": "chokepoint_speed", "chokepoint": "Hormuz", "tanker_avg_kn": 5.0, "baseline_kn": 12.0, "n": 14}])
    assert len(out) == 1
    p = out[0]
    assert p["rule"] == "tanker_slowdown" and {"WTI", "BRENT", "XAU/USD"} <= set(p["assets"])
    assert p["opens_trade"] is False and p["risk_action"] == "cut_size" and p["risk_action_applied"] is False
    assert rec.of("market_impact")[0]["note"].startswith("Tankers at Hormuz")


def test_small_slowdown_or_few_ships_is_ignored():
    out, _ = _run([{"kind": "chokepoint_speed", "chokepoint": "Suez", "tanker_avg_kn": 11.0, "baseline_kn": 12.0, "n": 14},
                   {"kind": "chokepoint_speed", "chokepoint": "Suez", "tanker_avg_kn": 2.0, "baseline_kn": 12.0, "n": 1}])
    assert out == []


def test_military_flight_surge_is_safe_haven_watch():
    out, _ = _run([{"kind": "mil_flights", "region": "Gulf", "count": 40, "baseline": 12}])
    assert out and "XAU/USD" in out[0]["assets"] and out[0]["risk_action"] == "pause_new"


def test_m6_quake_near_mine_hits_metals_far_or_small_does_not():
    near = {"kind": "quake", "id": "q1", "mag": 6.4, "lat": -24.0, "lon": -69.2, "place": "near Antofagasta"}
    far = {"kind": "quake", "id": "q2", "mag": 7.1, "lat": 10.0, "lon": -30.0, "place": "mid-Atlantic"}
    small = {"kind": "quake", "id": "q3", "mag": 5.2, "lat": -24.0, "lon": -69.2, "place": "near Antofagasta"}
    out, _ = _run([near, far, small])
    assert len(out) == 1 and "COPPER" in out[0]["assets"]


def test_frost_near_coffee_and_heat_near_cocoa():
    out, _ = _run([{"kind": "weather", "belt": "Minas Gerais coffee", "crop": "coffee", "tmin": 0.5, "tmax": 20, "precip_sum": 10, "days": 7},
                   {"kind": "weather", "belt": "Ghana cocoa", "crop": "cocoa", "tmin": 22, "tmax": 38, "precip_sum": 30, "days": 7},
                   {"kind": "weather", "belt": "Kansas wheat", "crop": "wheat", "tmin": 5, "tmax": 20, "precip_sum": 20, "days": 7}])
    assets = sorted(a for p in out for a in p["assets"])
    assert assets == ["COCOA", "COFFEE"]


def test_ndvi_drop_and_oil_stocks_rules():
    out, _ = _run([{"kind": "ndvi", "belt": "Iowa corn", "crop": "corn", "value": 30.0, "baseline": 50.0},
                   {"kind": "oil_stocks", "id": "2026-11-20", "change_mb": 9.0, "avg_change_mb": -1.0}])
    assert {p["rule"] for p in out} == {"crop_ndvi", "oil_stocks"}


def test_dedupe_same_day():
    ev = [{"kind": "mil_flights", "region": "Taiwan Strait", "count": 30, "baseline": 10}]
    assert len(impact.evaluate(ev)) == 1
    assert impact.evaluate(ev) == []


def test_risk_action_only_applied_when_user_says_apply():
    from nsq.settings import set as sset
    ev = [{"kind": "mil_flights", "region": "Korean Peninsula", "count": 50, "baseline": 10}]
    impact.evaluate(ev)
    assert impact.active_risk_flags() == []
    sset("godseye.risk_actions", "apply")
    ev[0]["region"] = "Eastern Mediterranean"
    out = impact.evaluate(ev)
    assert out[0]["risk_action_applied"] is True
    flags = impact.active_risk_flags("XAU/USD")
    assert flags and flags[0]["action"] == "pause_new"


def test_never_opens_a_trade():
    rec = h.Recorder()
    impact.evaluate([{"kind": "chokepoint_speed", "chokepoint": "Hormuz", "tanker_avg_kn": 1.0, "baseline_kn": 12.0, "n": 30},
                     {"kind": "mil_flights", "region": "Gulf", "count": 90, "baseline": 10}])
    rec.close()
    trade_events = {"order_sent", "order_filled", "position_update", "entry_state", "size_calc", "exit_done"}
    assert not trade_events & set(rec.types())
    src = open(impact.__file__).read() + open(layers.__file__).read() + open(altdata.__file__).read()
    assert "nsq.brokers" not in src and "nsq.flow" not in src and "order" not in impact.evaluate.__code__.co_names


def test_layers_degrade_offline_to_synthetic_then_cache():
    d = layers.get_layer("quakes")
    assert d["synthetic"] is True and d["features"] and d["attribution"].startswith("Earthquakes: U.S. Geological Survey")
    layers._cache_write("quakes", {"layer": "quakes", "attribution": layers.ATTRIBUTION["quakes"], "enabled": True,
                                   "features": [{"id": "x", "lat": 1, "lon": 2, "mag": 5.0}], "synthetic": False, "cached": False})
    d2 = layers.get_layer("quakes")
    assert d2["cached"] is True and d2["synthetic"] is False and d2["features"][0]["id"] == "x"


def test_synthetic_layers_never_raise_impacts():
    syn = {"quakes": {"features": [{"id": "s", "mag": 7.5, "lat": -24.2, "lon": -69.1}], "synthetic": True}}
    assert impact.events_from_layers(syn) == []


def test_byo_key_layers_are_off_and_explain():
    assert layers.enabled("ships") is False and layers.enabled("fires") is False
    with pytest.raises(PermissionError):
        layers.fetch_ships()
    assert altdata.oil_storage()["ok"] is False
    assert altdata.car_counts()["locked"] is True


def test_layer_flags_and_attribution_for_every_layer():
    for name in layers.FETCHERS:
        assert layers.ATTRIBUTION[name]
        assert f"godseye.layer.{name}.enabled" in layers.DEFAULTS
