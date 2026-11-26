"""Candles (cache, resample, synthetic fallback), order flow, profiles, calendar."""
import json

import numpy as np
import pandas as pd
import pytest

import stage3_helpers as h
from nsq.data import candles, news, orderflow, profile, synthetic


def test_synthetic_is_flagged_seeded_and_stable():
    a = synthetic.candles("XAU/USD", "1h", "2020-01-01", "2020-03-01")
    b = synthetic.candles("XAU/USD", "1h", "2020-02-01", "2021-06-01")
    assert a.attrs["synthetic"] is True and "tick" in a.attrs["volume_kind"]
    common = a.index.intersection(b.index)
    assert len(common) > 100 and (a.loc[common] == b.loc[common]).all().all()
    r = np.log(b["close"]).diff().dropna()
    assert 0.08 < r.std() * np.sqrt(252 * 23) < 0.30          # gold-like annual volatility
    assert (a["high"] >= a[["open", "close"]].max(axis=1)).all() and (a["low"] <= a[["open", "close"]].min(axis=1)).all()
    assert not ((a.index.dayofweek == 5)).any()               # gold is closed on Saturday


def test_get_falls_back_to_synthetic_offline():
    df = candles.get("BTC/USD", "15m", "2025-01-01", "2025-01-03")
    assert df.attrs["synthetic"] is True and len(df) == 192


def test_cache_roundtrip_and_closed_bars_only_resample():
    idx = pd.date_range("2025-01-01", periods=10, freq="1min", tz="UTC")
    one = pd.DataFrame({"open": range(10), "high": range(1, 11), "low": range(10), "close": range(10), "volume": 1.0}, index=idx, dtype=float)
    candles.write_cache("ETH/USD", "1m", one)
    back = candles.read_cache("ETH/USD", "1m")
    assert len(back) == 10 and back.index.tz is not None
    r3 = candles.resample(back, "3m", drop_incomplete=True, base_minutes=1)
    assert len(r3) == 3                                        # 00-02, 03-05, 06-08; 09 alone is incomplete
    assert r3.iloc[0].open == 0 and r3.iloc[0].close == 2 and r3.iloc[0].high == 3 and r3.iloc[0].volume == 3
    got = candles.get("ETH/USD", "3m", "2025-01-01", "2025-01-01 00:10")
    assert got.attrs["synthetic"] is False and len(got) == 3


def test_registered_broker_provider_wins():
    df = synthetic.candles("XAU/USD", "15m", "2025-01-01", "2025-01-02")
    candles.register_provider("testbroker", lambda m, tf, s, e: df if m == "XAU/USD" else None)
    got = candles.get("XAU/USD", "15m", "2025-01-01", "2025-01-02")
    assert got.attrs["source"] == "broker:testbroker" and got.attrs["volume_kind"] == "tick" and got.attrs["synthetic"] is False
    candles._providers.clear()


def test_profile_poc_value_area():
    prices = [100] * 50 + [101] * 30 + [99] * 10 + [105] * 2 + [95] * 2
    pr = profile.from_trades(prices, np.ones(len(prices)), bins=11)
    assert abs(pr["poc"] - 100) < 0.6
    assert pr["val"] <= 100 and pr["vah"] >= 100.5 and pr["vah"] <= 102.5
    vol = sum(b["vol"] for b in pr["bins"] if pr["val"] <= b["price"] <= pr["vah"])
    assert vol >= 0.7 * len(prices)


def test_gold_profile_is_labelled_tick_volume():
    df = synthetic.candles("XAU/USD", "15m", "2025-01-06", "2025-01-07")
    pr = profile.from_candles(df)
    assert "tick-volume" in pr["label"]


def test_kraken_ws_parser_and_bubbles():
    msg = {"channel": "trade", "type": "update", "data": [
        {"symbol": "BTC/USD", "side": "buy", "price": 60840.2, "qty": 0.13, "ord_type": "limit", "trade_id": 1, "timestamp": "2026-11-26T04:10:28.923763Z"}]}
    t = orderflow.parse_kraken_trade_msg(msg)
    assert t[0][1:] == (60840.2, 0.13, "buy", "BTC/USD")
    assert orderflow.parse_kraken_trade_msg({"channel": "heartbeat"}) == []
    rec = h.Recorder()
    eng = orderflow.OrderFlowEngine("BTC/USD", profile_every_s=1e9, min_bubble=1.0)
    rng = np.random.default_rng(0)
    for i in range(400):
        eng.on_trade(1000.0 + i, 60000 + rng.normal(0, 5), float(rng.exponential(0.05)), "buy" if i % 2 else "sell")
    # one big taker order sweeping three levels (same timestamp, same side) -> one bubble
    for px in (60010, 60011, 60012):
        eng.on_trade(2000.0, px, 3.0, "buy")
    eng.on_trade(2001.0, 60000, 0.01, "sell")
    b = rec.of("orderflow_bubble")
    assert len(b) == 1 and b[0]["side"] == "buy" and b[0]["size"] == pytest.approx(9.0) and b[0]["levels"] == 3
    p = eng.emit_profile()
    assert rec.of("profile_update") and p["poc"] is not None and p["val"] <= p["poc"] <= p["vah"]
    rec.close()


def test_tick_profile_for_gold():
    tp = orderflow.TickProfile("XAU/USD", profile_every_s=1e9)
    for i in range(100):
        tp.on_tick(float(i), 2650 + (i % 5) * 0.1)
    p = tp.emit_profile()
    assert p["volume_kind"] == "tick" and p["label"] == "tick-volume profile"
    with pytest.raises(TypeError):
        tp.on_trade(0, 1, 1, "buy")


def test_calendar_rules_and_blackout():
    evs = news.calendar("2026-12-01", "2026-12-31")
    nfp = [e for e in evs if "Non-Farm" in e["title"]]
    assert len(nfp) == 1 and nfp[0]["time"].startswith("2026-12-04T13:30")     # first Friday, 08:30 New York
    fomc = [e for e in evs if "FOMC" in e["title"]]
    assert fomc and fomc[0]["time"].startswith("2026-12-09T19:00")
    assert news.in_blackout("2026-12-04T13:40:00Z", 15)["title"] == "US Non-Farm Payrolls"
    assert news.in_blackout("2026-12-04T14:00:00Z", 15) is None


def test_rss_and_atom_parsing_headline_and_link_only():
    rss = b"<rss><channel><item><title>Fed holds</title><link>https://x/a</link><description>long body</description></item></channel></rss>"
    atom = b'<feed xmlns="http://www.w3.org/2005/Atom"><entry><title>8-K Acme</title><link href="https://sec/x"/><updated>2026</updated></entry></feed>'
    a, b = news.parse_feed(rss, "t"), news.parse_feed(atom, "t")
    assert a[0]["title"] == "Fed holds" and a[0]["url"] == "https://x/a" and "description" not in json.dumps(a)
    assert b[0]["url"] == "https://sec/x"
    with pytest.raises(Exception):
        news.parse_feed(b'<?xml version="1.0"?><!DOCTYPE x [<!ENTITY a "b">]><rss>&a;</rss>', "t")


def test_congress_and_sec_need_opt_in():
    with pytest.raises(PermissionError):
        news.house_ptrs(2026)
    with pytest.raises(PermissionError):
        news.sec_current_8k()
    got = news.poll()                        # everything offline or not configured: nothing crashes
    assert isinstance(got, dict)
