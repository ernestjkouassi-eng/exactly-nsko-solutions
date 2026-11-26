"""Knowledge Base detectors on hand-made candles, and the concept lifecycle."""
import pandas as pd

import stage3_helpers as h
from nsq.lab import detectors as d
from nsq.lab import kb


def test_bullish_and_bearish_fvg():
    df = h.candles([(100, 101, 99, 100.5), (100.5, 106, 100.4, 105.8), (105.8, 107, 102, 106.5),   # gap 101..102
                    (106.5, 107, 104, 104.5), (104.5, 104.6, 98, 98.2), (98.2, 103, 97, 97.5)])    # bearish gap 104..103? no
    ev = d.fair_value_gaps(df)
    bull = ev[ev.dir == 1].iloc[0]
    assert bull.time == df.index[2] and bull.bottom == 101 and bull.top == 102 and bull["size"] == 1
    df2 = h.candles([(110, 111, 109, 109.5), (109.5, 109.6, 104, 104.2), (104.2, 108, 103, 103.5)])  # low1 109 > high3 108
    ev2 = d.fair_value_gaps(df2)
    assert len(ev2) == 1 and ev2.iloc[0].dir == -1 and ev2.iloc[0].top == 109 and ev2.iloc[0].bottom == 108


def test_swings_confirm_only_after_n_bars():
    rows = [(100, 101, 99, 100), (100, 102, 99, 101), (101, 105, 100, 104), (104, 103, 101, 102), (102, 102, 100, 101), (101, 101, 99, 100)]
    df = h.candles(rows)
    sw = d.swings(df, n=2)
    hi = sw[sw.dir == -1].iloc[0]
    assert hi.origin == df.index[2] and hi.time == df.index[4] and hi.top == 105


def _structure_series():
    # up-leg to a swing high at 110, pull back to a swing low at 104, break above 110 (BOS up),
    # then fall through the swing low (CHoCH down)
    rows = [(100, 101, 99, 100), (100, 104, 99.5, 103), (103, 107, 102, 106), (106, 110, 105, 108), (108, 108.5, 106, 107),
            (107, 107.5, 105, 105.5), (105.5, 106, 104, 104.5), (104.5, 106, 104.2, 105.8), (105.8, 108, 105, 107.5),
            (107.5, 111.5, 107, 111), (111, 112, 110, 111.5), (111.5, 111.8, 108, 108.5), (108.5, 109, 105, 105.5),
            (105.5, 106, 102, 102.5), (102.5, 103, 101, 101.5)]
    return h.candles(rows)


def test_bos_then_choch():
    df = _structure_series()
    bos, choch = d.structure(df, n=2)
    assert len(bos) >= 1 and bos.iloc[0].dir == 1 and bos.iloc[0].top == 110
    assert len(choch) >= 1 and choch.iloc[0].dir == -1
    assert choch.iloc[0].time > bos.iloc[0].time


def test_liquidity_sweep_wick_below_swing_low_then_reclaim():
    rows = [(101, 102, 100, 100.5), (100, 101, 99, 100), (100, 100.5, 97, 98), (98, 99, 98, 98.8), (98.8, 100, 98.5, 99.5),
            (99.5, 100, 99, 99.6), (99.6, 100, 96.5, 98.5)]   # swing low 97 (bar 2) confirmed at bar 4; bar 6 sweeps it
    df = h.candles(rows)
    ev = d.liquidity_sweeps(df, n=2)
    s = ev.iloc[0]
    assert s.dir == 1 and s.time == df.index[6] and s.top == 97 and s.bottom == 96.5


def test_displacement_needs_big_body():
    rows = [(100, 100.6, 99.4, 100.1)] * 20 + [(100, 104, 99.9, 103.9)]
    ev = d.displacement(h.candles(rows))
    assert len(ev) == 1 and ev.iloc[0].dir == 1


def test_order_block_is_last_opposite_candle_before_break():
    df = _structure_series()
    ob = d.order_blocks(df, n=2)
    bull = ob[ob.dir == 1].iloc[0]
    # the last down candle before the bullish break at bar 9 is bar 6 (105.5 -> 104.5)
    assert bull.origin == df.index[6] and bull.top == 106 and bull.bottom == 104


def test_inside_bar_and_equal_highs():
    df = h.candles([(100, 105, 95, 101), (101, 104, 96, 102), (102, 106, 97, 99)])
    ib = d.inside_bars(df)
    assert list(ib.time) == [df.index[1]]
    rows = [(100, 101, 99, 100)] * 14 + [(100, 101, 99, 100), (100, 110, 99.5, 109), (109, 109.5, 105, 106), (106, 107, 104, 105), (105, 110.02, 104.5, 109),
            (109, 109.2, 105, 106), (106, 106.5, 103, 104)] + [(104, 104.5, 103.5, 104)] * 14
    eq = d.equal_levels(h.candles(rows), n=2, tol_atr=0.5)
    assert len(eq[eq.dir == -1]) == 1


def test_asia_range_confirmed_at_its_last_bar():
    idx = pd.date_range("2025-01-06 00:00", periods=40, freq="15min", tz="UTC")
    df = pd.DataFrame({"open": 100.0, "high": 101.0, "low": 99.0, "close": 100.0, "volume": 1.0}, index=idx)
    df.loc[idx[5], "high"] = 103.0
    ev = d.session_range(df, 0, 7)
    assert ev.iloc[0].time == idx[27] and ev.iloc[0].top == 103.0


def test_detectors_never_look_ahead():
    from nsq.data import synthetic
    df = synthetic.candles("XAU/USD", "15m", "2024-03-01", "2024-04-01")
    cut = len(df) * 2 // 3
    for name, fn in d.DETECTORS.items():
        full, part = fn(df), fn(df.iloc[:cut])
        last = df.index[cut - 1]
        a = full[full.time <= last].reset_index(drop=True)
        b = part.reset_index(drop=True)
        pd.testing.assert_frame_equal(a, b, check_dtype=False, obj=name)


def test_kb_lifecycle_and_stats():
    from nsq.data import synthetic
    assert kb.seed() == len(kb.CONCEPTS)
    c = kb.get("fair_value_gap")
    assert c["stage_name"] == "coded" and len(c["sources"]) == 3 and "def fair_value_gaps" in c["code_src"]
    assert c["rule"] and c["bullish"] and c["bearish"]
    df = synthetic.candles("XAU/USD", "15m", "2024-03-01", "2024-04-01")
    st = kb.measure(df, ["fair_value_gap", "order_block"])
    assert st["fair_value_gap"]["count"] > 0 and 0 <= st["fair_value_gap"]["pct_filled"] <= 100
    assert st["fair_value_gap"]["avg_size"] > 0 and st["fair_value_gap"]["synthetic"] is True
    assert kb.get("fair_value_gap")["stage"] == 4
    kb.mark_tested("fair_value_gap")
    assert kb.set_verdict("fair_value_gap", "keep")["stage_name"] == "verdict"
    assert kb.LIFECYCLE == ["found", "explained", "coded", "measured", "tested", "verdict"]
    slug = kb.add_found("breaker block", {"title": "t", "url": "u"})
    assert kb.get(slug)["stage"] == 1
