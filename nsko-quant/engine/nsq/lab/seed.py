"""Seed strategy pack: NSKO-OF-1 for gold and bitcoin, plus three plain baselines to beat.

Seeding writes the recipes, and a `strategies` row (status "lab") with version 1 holding the recipe,
so they show in the Strategies list. Nothing is promoted to paper or live here: a strategy only
earns that by clearing the bar on real data.
"""
from __future__ import annotations

PACK: list[dict] = [
    {"id": "nsko-of-1-xau", "name": "NSKO-OF-1 XAU", "market": "XAU/USD", "timeframe": "3m", "idea_type": "Orderflow",
     "entry": {"type": "nsko_of_1"}, "stop": {"type": "level", "mult": 1.0}, "target": {"type": "level", "r": 2.0},
     "filters": {"session": ["london", "ny"], "news_blackout_min": 15},
     "params": {"htf": "15m", "level_tol_atr": 0.25, "sweep_eps_atr": 0.05, "vol_mult": 1.8, "stop_buf_atr": 0.15,
                "min_rr": 1.2, "fallback_r": 2.0, "max_per_session": 3, "accept_bars": 3, "atr_n": 14,
                "vol_n": 50, "profile_bins": 40},
     "notes": "Tick-volume profile (gold is a CFD: no exchange volume). Pair 15m levels + 3m trigger."},
    {"id": "nsko-of-1-btc", "name": "NSKO-OF-1 BTC", "market": "BTC/USD", "timeframe": "5m", "idea_type": "Orderflow",
     "entry": {"type": "nsko_of_1"}, "stop": {"type": "level", "mult": 1.0}, "target": {"type": "level", "r": 2.0},
     "filters": {"session": None, "news_blackout_min": 15},
     "params": {"htf": "1h", "level_tol_atr": 0.25, "sweep_eps_atr": 0.05, "vol_mult": 2.0, "stop_buf_atr": 0.15,
                "min_rr": 1.2, "fallback_r": 2.0, "max_per_session": 4, "accept_bars": 3, "atr_n": 14,
                "vol_n": 50, "profile_bins": 40, "liquidity_frac": 0.6},
     "notes": "Real exchange volume (Kraken). Pair 1h levels + 5m trigger. 24/7 with a liquidity filter."},
    {"id": "trend-xau", "name": "Trend-XAU", "market": "XAU/USD", "timeframe": "1h", "idea_type": "Trend following",
     "entry": {"type": "ema_cross"}, "stop": {"type": "atr", "mult": 2.0}, "target": {"type": "r", "r": 2.0},
     "filters": {"session": None, "news_blackout_min": 15}, "params": {"fast": 20, "slow": 50, "atr_n": 14}},
    {"id": "orb-xau", "name": "ORB-XAU", "market": "XAU/USD", "timeframe": "15m", "idea_type": "Breakout",
     "entry": {"type": "orb"}, "stop": {"type": "level", "mult": 1.0}, "target": {"type": "r", "r": 1.6},
     "filters": {"session": ["london", "ny"], "news_blackout_min": 15},
     "params": {"open_hour": 7.0, "range_minutes": 30, "last_entry_hour": 12.0, "atr_n": 14}},
    {"id": "vwap-rev-btc", "name": "VWAP-Rev-BTC", "market": "BTC/USD", "timeframe": "15m", "idea_type": "Mean reversion",
     "entry": {"type": "vwap_reversion"}, "stop": {"type": "atr", "mult": 1.5}, "target": {"type": "level", "r": 1.5},
     "filters": {"session": None, "news_blackout_min": 15}, "params": {"k": 2.0, "dev_n": 50, "atr_n": 14, "min_session_bars": 4}},
]


def seed_pack() -> list[str]:
    from .runner import save_recipe, upsert_strategy
    from nsq.db import conn
    ids = []
    for r in PACK:
        rid = save_recipe(dict(r), origin="seed")
        if conn().execute("SELECT 1 FROM strategies WHERE id=?", (rid,)).fetchone() is None:
            upsert_strategy(rid, r["name"], r["market"], r["timeframe"], r, None, "seed pack · not yet tested")
        ids.append(rid)
    return ids
