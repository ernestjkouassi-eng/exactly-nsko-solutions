"""No look-ahead: for every signal generator, appending future bars never changes earlier signals,
and signals computed on a truncated history equal the full-history signals up to the cut."""
import copy

import pandas as pd
import pytest

import stage3_helpers  # noqa: F401  (setup)
from nsq.data import synthetic
from nsq.lab import signals
from nsq.lab.seed import PACK


def _cases():
    out = []
    for r in PACK:
        tf = r["timeframe"]
        days = {"3m": 12, "5m": 15, "15m": 60, "1h": 200}[tf]
        out.append(pytest.param(r, days, id=r["id"]))
    # a variant with different params per generator, to cover more code paths
    v = copy.deepcopy([p for p in PACK if p["id"] == "nsko-of-1-btc"][0])
    v["params"].update(vol_mult=1.2, level_tol_atr=0.5, use_fvg=False)
    v["id"] = "of1-variant"
    out.append(pytest.param(v, 15, id="of1-variant"))
    return out


@pytest.mark.parametrize("recipe,days", _cases())
def test_no_look_ahead(recipe, days):
    end = pd.Timestamp("2025-03-01", tz="UTC")
    df = synthetic.candles(recipe["market"], recipe["timeframe"], end - pd.Timedelta(days=days), end)
    full = signals.generate(recipe, df)
    assert len(full) > 0, "test data should produce signals"
    n = len(df)
    for cut in (int(n * 0.45), int(n * 0.7), n - 7):
        part = df.iloc[:cut]
        last = part.index[-1].isoformat()
        got = signals.generate(recipe, part)
        expect = [s for s in full if s["time"] <= last]
        assert got == expect, f"signals changed when future bars were added (cut {cut})"
    for s in full:
        assert s["side"] in ("buy", "sell")
        assert (s["entry"] - s["stop"]) * (1 if s["side"] == "buy" else -1) > 0
        assert (s["target"] - s["entry"]) * (1 if s["side"] == "buy" else -1) > 0
        assert pd.Timestamp(s["time"]) in df.index


def test_future_bars_appended_do_not_change_signals():
    r = [p for p in PACK if p["id"] == "trend-xau"][0]
    df = synthetic.candles("XAU/USD", "1h", "2024-01-01", "2024-07-01")
    base = signals.generate(r, df.iloc[:2000])
    more = signals.generate(r, df)
    assert more[: len(base)] == base


def test_signal_shape_matches_contract():
    r = [p for p in PACK if p["id"] == "orb-xau"][0]
    df = synthetic.candles("XAU/USD", "15m", "2024-01-01", "2024-02-01")
    s = signals.generate(r, df)[0]
    assert set(s) == {"time", "side", "entry", "stop", "target", "reason"}


def test_session_filter_london_ny_for_gold():
    r = [p for p in PACK if p["id"] == "nsko-of-1-xau"][0]
    df = synthetic.candles("XAU/USD", "3m", "2025-01-01", "2025-01-20")
    for s in signals.generate(r, df):
        h = pd.Timestamp(s["time"]).hour + pd.Timestamp(s["time"]).minute / 60
        assert 7 <= h < 20, s


def test_unknown_generator_rejected():
    with pytest.raises(ValueError):
        signals.generate({"entry": {"type": "magic"}}, synthetic.candles("BTC/USD", "1h", "2024-01-01", "2024-01-10"))
