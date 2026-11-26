"""Backtester maths on a known series, walk-forward split, PBO on toy cases, Monte Carlo, runner."""
import numpy as np
import pandas as pd
import pytest

import stage3_helpers as h
from nsq.lab import backtest as bt
from nsq.lab import overfit, walkforward

ZERO = {"spread": 0.0, "spread_bps": 0.0, "slippage_bps": 0.0, "commission_bps": 0.0, "funding_annual_pct": 0.0}


def _df():
    # bar0 signal; bar1 opens 100 (fill); bar2 reaches 111 -> target 110
    return h.candles([(99, 100, 98, 99.5), (100, 105, 99, 104), (104, 111, 103, 109), (109, 110, 108, 109), (109, 109, 107, 108)])


def _sig(df, i=0, side="buy", stop=95.0, target=110.0):
    return [{"time": df.index[i].isoformat(), "side": side, "entry": float(df.close.iloc[i]), "stop": stop, "target": target, "reason": "t"}]


def test_target_hit_zero_costs_is_exactly_2R():
    df = _df()
    r = bt.run(df, _sig(df), costs=ZERO, risk_pct=1.0, market="BTC/USD")
    t = r.trades.iloc[0]
    assert t.entry == 100 and t.exit == 110 and t.exit_reason == "target"
    assert t.r == pytest.approx(2.0)
    assert r.equity.iloc[-1] == pytest.approx(1.02)
    assert t.entry_time == df.index[1]            # fills on the bar AFTER the signal


def test_costs_by_hand():
    df = _df()
    c = {"spread": 0.2, "spread_bps": 0.0, "slippage_bps": 10.0, "commission_bps": 5.0, "funding_annual_pct": 0.0}
    t = bt.run(df, _sig(df), costs=c, market="BTC/USD").trades.iloc[0]
    fill = 100 + 0.1 + 100 * 10 / 1e4             # half spread + slippage on the market entry
    exit_px = 110 - 0.1                            # limit target: half spread, no slippage
    comm = (fill + exit_px) * 5 / 1e4
    risk = fill - 95
    assert t.entry == pytest.approx(fill)
    assert t.exit == pytest.approx(exit_px)
    assert t.r == pytest.approx((exit_px - fill - comm) / risk)


def test_stop_first_when_bar_touches_both():
    df = h.candles([(100, 100, 100, 100), (100, 101, 99, 100), (100, 112, 94, 100), (100, 100, 100, 100)])
    t = bt.run(df, _sig(df), costs=ZERO, market="BTC/USD").trades.iloc[0]
    assert t.exit_reason == "stop" and t.r == pytest.approx(-1.0)


def test_gap_through_stop_fills_at_open():
    df = h.candles([(100, 100, 100, 100), (100, 101, 99, 100), (90, 91, 89, 90), (90, 90, 90, 90)])
    t = bt.run(df, _sig(df), costs=ZERO, market="BTC/USD").trades.iloc[0]
    assert t.exit == 90 and t.r == pytest.approx(-2.0)


def test_short_trade_and_funding_nights():
    rows = [(100, 100, 100, 100)] * 2 + [(100, 101, 99, 100)] * 200 + [(100, 100, 89, 90)]
    df = h.candles(rows, start="2025-01-06 00:00", freq="1h")
    c = dict(ZERO, funding_annual_pct=36.5)
    t = bt.run(df, _sig(df, 0, "sell", stop=105, target=90), costs=c, market="XAU/USD").trades.iloc[0]
    nights = bt._rollovers(df.index[1].value, t.exit_time.value)
    assert t.nights == nights and nights == 8
    assert t.funding == pytest.approx(100 * 0.365 / 365 * nights)
    assert t.r == pytest.approx((10 - t.funding) / 5)


def test_one_position_at_a_time():
    df = _df()
    sigs = _sig(df, 0) + _sig(df, 1)
    assert len(bt.run(df, sigs, costs=ZERO, market="BTC/USD").trades) == 1


def test_drawdown_and_sharpe_known():
    eq = pd.Series([1.0, 1.1, 0.99, 1.2], index=pd.date_range("2025-01-01", periods=4, freq="D", tz="UTC"))
    assert bt.max_drawdown_pct(eq) == pytest.approx(-10.0)
    d = bt.daily_returns(eq)
    exp = d.mean() / d.std(ddof=1) * np.sqrt(252)
    assert bt.sharpe(d, 252) == pytest.approx(exp)
    assert bt.sharpe(pd.Series([0.01, 0.01, 0.01]), 252) == 0.0   # zero variance -> 0, not inf


def test_downsample_keeps_ends():
    eq = pd.Series(np.linspace(1, 2, 1000), index=pd.date_range("2025-01-01", periods=1000, freq="h", tz="UTC"))
    ds = bt.downsample(eq, 50)
    assert len(ds) == 50 and ds[0][1] == 1.0 and ds[-1][1] == 2.0


def test_walkforward_calendar_split():
    idx = pd.date_range("2009-01-01", "2025-12-31", freq="D", tz="UTC")
    sp = walkforward.split(idx)
    assert sp.mode == "calendar" and sp.oos_start == pd.Timestamp("2020-01-01", tz="UTC")
    assert sp.is_mask(idx).sum() + sp.oos_mask(idx).sum() == len(idx)
    assert not (sp.is_mask(idx) & sp.oos_mask(idx)).any()


def test_walkforward_fallback_when_history_is_short():
    idx = pd.date_range("2024-01-01", "2025-01-01", freq="h", tz="UTC")
    sp = walkforward.split(idx)
    assert sp.mode == "fraction"
    assert sp.oos_start == idx[0] + 0.7 * (idx[-1] - idx[0])


def test_pbo_toy_cases():
    rng = np.random.default_rng(1)
    noise = rng.normal(0, 0.01, (480, 10))
    p_noise = overfit.pbo_cscv(noise, S=16)["pbo"]
    assert 0.25 <= p_noise <= 0.75                 # pure noise: picking the IS winner is a coin flip
    edge = noise.copy()
    edge[:, 3] += 0.004                            # one variant truly better everywhere
    assert overfit.pbo_cscv(edge, S=16)["pbo"] < 0.05
    # overfit by construction: the IS winner is the OOS loser in every split
    T = 160
    blocks = np.repeat(np.arange(16), T // 16)
    sign = np.where(blocks % 2 == 0, 1.0, -1.0)
    M = np.stack([sign * (k - 4.5) * 0.001 + rng.normal(0, 1e-5, T) for k in range(10)], axis=1)
    res = overfit.pbo_cscv(M, S=16)
    assert res["pbo"] > 0.5


def test_sharpe_decline():
    assert overfit.sharpe_decline(2.0, 1.0) == pytest.approx(0.5)
    assert overfit.sharpe_decline(2.0, 3.0) == 0.0


def test_monte_carlo_drawdown_odds():
    r = np.array([1.0, -1.0] * 50)
    mc = overfit.monte_carlo_dd(r, risk_pct=1.0, n=300, bad_dd_pct=-5)
    assert mc["dd_p95"] <= mc["dd_p50"] <= 0
    assert 0 <= mc["p_bad"] <= 100 and len(mc["fan"]["p50"]) > 2


def test_chance_score_ranks_random_entries():
    from nsq.data import synthetic
    df = synthetic.candles("BTC/USD", "1h", "2024-01-01", "2024-04-01")
    sigs = [{"time": df.index[i].isoformat(), "side": "buy", "entry": float(df.close.iloc[i]),
             "stop": float(df.close.iloc[i]) * 0.99, "target": float(df.close.iloc[i]) * 1.02, "reason": "x"} for i in range(30, 2000, 60)]
    res = overfit.chance_score(df, sigs, actual_metric=10.0, n_random=10, costs=ZERO, market="BTC/USD")
    assert res["percentile"] == 100.0          # an impossible 10R average beats every random run


def test_runner_emits_contract_payloads():
    from nsq.data import synthetic
    from nsq.lab import runner
    from nsq.lab.seed import PACK
    rec = dict([p for p in PACK if p["id"] == "trend-xau"][0])
    df = synthetic.candles("XAU/USD", "1h", "2017-01-01", "2023-01-01")
    rec_ = h.Recorder()
    s = runner.run_recipe(rec, candles=df, n_variants=4, chance_runs=5, mc_runs=100)
    vt = rec_.of("variant_tested")
    assert len(vt) == 4
    keys = {"id", "recipe", "market", "tf", "sharpeIS", "sharpeOOS", "trades", "win", "rr", "dd", "outcome", "why", "seed"}
    assert all(set(v) == keys for v in vt)
    assert all(v["outcome"] in ("clear", "sieve", "failed") for v in vt)
    assert rec_.of("backtest_done") and s["synthetic"] is True
    from nsq.db import conn
    assert conn().execute("SELECT COUNT(*) n FROM variants").fetchone()["n"] == 4
    eq = conn().execute("SELECT equity_json FROM backtests LIMIT 1").fetchone()["equity_json"]
    assert len(pd.read_json(__import__("io").StringIO(eq))) > 2
    # synthetic results never become strategies
    assert conn().execute("SELECT COUNT(*) n FROM strategy_versions WHERE note LIKE 'cleared%'").fetchone()["n"] == 0
    rec_.close()


def test_variants_x10_are_seeded_and_distinct():
    from nsq.lab import runner
    from nsq.lab.seed import PACK
    rec = [p for p in PACK if p["id"] == "nsko-of-1-xau"][0]
    a, b = runner.make_variants(rec, 10), runner.make_variants(rec, 10)
    assert a == b and len(a) == 10
    assert len({str(p) for _, p in a}) == 10
    assert a[0][1] == rec["params"]


def test_judge_outcomes_and_thresholds_from_settings():
    from nsq.lab import runner
    from nsq.settings import set as sset
    good = {"trades": 80, "expectancy_r": 0.3, "dd": -8.0, "sharpe": 1.6, "win": 50, "rr": 1.5}
    b = runner.bar()
    assert runner.judge(good, good, {}, b)[0] == "clear"
    assert runner.judge(good, dict(good, sharpe=1.0), {}, b)[0] == "sieve"
    assert runner.judge(good, dict(good, trades=5), {}, b) == ("failed", "Too few trades")
    assert runner.judge(good, good, {"stability": {"ratio": 0.2, "worst_sharpe_oos": 0.3}}, b) == ("sieve", "Unstable under ±20% parameter change")
    sset("lab.bar.oos_sharpe", 2.0)
    assert runner.bar()["oos_sharpe"] == 2.0
    assert runner.judge(good, good, {}, runner.bar())[0] == "sieve"
