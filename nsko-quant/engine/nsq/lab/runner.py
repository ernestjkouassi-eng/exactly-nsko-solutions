"""Lab runner: variants x10 -> backtest with costs -> walk-forward IS/OOS -> the bar -> store + events.

The bar (all thresholds in settings, defaults below):
  lab.bar.oos_sharpe        1.40   OOS Sharpe after costs
  lab.bar.min_trades        30     OOS trades
  lab.bar.max_dd_pct        20     max drawdown (% of equity, OOS)
  lab.bar.stability_ratio   0.5    worst OOS Sharpe under +/-20 % parameter changes, as a share of
                                   the unchanged OOS Sharpe (and it must stay > 0)
  lab.bar.max_pbo           0.5    probability of backtest overfitting (CSCV across the variants)
  lab.bar.max_decline       0.6    share of IS Sharpe that may be lost OOS
  lab.bar.min_chance_pct    90     must beat this % of random-entry runs (expectancy in R)
  lab.bar.sieve_sharpe      0.7    below the bar but above this -> "sieve" (kept for a closer look)
Outcomes: clear (passes everything), sieve (OOS Sharpe >= sieve_sharpe, enough trades, drawdown
inside the limit, but fails the bar or a robustness check), failed.
"""
from __future__ import annotations

import copy
import json
import zlib

import numpy as np
import pandas as pd

from nsq.data import candles as candles_mod
from nsq.data.markets import info, norm, tf_minutes
from nsq.data.util import audit_safe, emit, ensure_table, jdump, log, now_ms, setting

from . import backtest as bt
from . import overfit, signals, walkforward

DEFAULTS = {
    "lab.bar.oos_sharpe": 1.40, "lab.bar.min_trades": 30, "lab.bar.max_dd_pct": 20.0,
    "lab.bar.stability_ratio": 0.5, "lab.bar.max_pbo": 0.5, "lab.bar.max_decline": 0.6,
    "lab.bar.min_chance_pct": 90.0, "lab.bar.sieve_sharpe": 0.7,
    "lab.variants_per_recipe": 10, "lab.risk_pct": 1.0, "lab.chance_runs": 60, "lab.mc_runs": 1000,
    "lab.history_start": "2009-01-01",
}
NON_TUNABLE = {"htf", "open_hour", "last_entry_hour", "apply_news", "use_fvg", "generator"}


def bar() -> dict:
    return {k.split(".")[-1]: setting(k, DEFAULTS) for k in DEFAULTS if k.startswith("lab.bar.")}


# ------------------------------------------------------------------------------------------- db

def ensure() -> None:
    from nsq.db import conn
    c = conn()
    ensure_table(c, "recipes", {"id": "TEXT PRIMARY KEY", "name": "TEXT", "market": "TEXT", "timeframe": "TEXT",
                                "idea_type": "TEXT", "json_rules": "TEXT", "source_id": "INTEGER", "origin": "TEXT",
                                "status": "TEXT DEFAULT 'new'", "created_at": "INTEGER"})
    ensure_table(c, "variants", {"id": "INTEGER PRIMARY KEY AUTOINCREMENT", "recipe_id": "TEXT", "label": "TEXT",
                                 "seed": "INTEGER", "params_json": "TEXT", "market": "TEXT", "tf": "TEXT",
                                 "sharpe_is": "REAL", "sharpe_oos": "REAL", "trades": "INTEGER", "win": "REAL",
                                 "rr": "REAL", "dd": "REAL", "outcome": "TEXT", "why": "TEXT", "metrics_json": "TEXT",
                                 "synthetic": "INTEGER", "created_at": "INTEGER"})
    ensure_table(c, "backtests", {"id": "INTEGER PRIMARY KEY AUTOINCREMENT", "variant_id": "INTEGER", "recipe_id": "TEXT",
                                  "market": "TEXT", "tf": "TEXT", "start": "TEXT", "end": "TEXT", "split_json": "TEXT",
                                  "costs_json": "TEXT", "metrics_is": "TEXT", "metrics_oos": "TEXT", "pbo": "REAL",
                                  "chance_json": "TEXT", "mc_json": "TEXT", "stability_json": "TEXT",
                                  "equity_json": "TEXT", "synthetic": "INTEGER", "data_source": "TEXT",
                                  "created_at": "INTEGER"})


def save_recipe(recipe: dict, source_id: int | None = None, origin: str = "lab") -> str:
    ensure()
    from nsq.db import conn
    rid = recipe.get("id") or f"r-{zlib.crc32(jdump(recipe).encode()):08x}"
    recipe["id"] = rid
    conn().execute("INSERT OR REPLACE INTO recipes (id, name, market, timeframe, idea_type, json_rules, source_id, origin, status, created_at)"
                   " VALUES (?,?,?,?,?,?,?,?,COALESCE((SELECT status FROM recipes WHERE id=?),'new'),?)",
                   (rid, recipe.get("name", rid), recipe.get("market"), recipe.get("timeframe"), recipe.get("idea_type"),
                    jdump(recipe), source_id, origin, rid, now_ms()))
    return rid


def load_recipe(rid: str) -> dict | None:
    ensure()
    from nsq.db import conn
    r = conn().execute("SELECT json_rules FROM recipes WHERE id=?", (rid,)).fetchone()
    return json.loads(r["json_rules"]) if r else None


def upsert_strategy(sid: str, name: str, market: str, tf: str, rules: dict, metrics: dict | None, note: str,
                    status: str = "lab") -> None:
    """Write to the core `strategies` + `strategy_versions` tables (schema owned by nsq.db)."""
    from nsq.db import conn
    import time
    c = conn()
    t = time.time()
    row = c.execute("SELECT id, status FROM strategies WHERE id=?", (sid,)).fetchone()
    if row is None:
        c.execute("INSERT INTO strategies (id, name, market, timeframe, status, intraday, created_at, updated_at)"
                  " VALUES (?,?,?,?,?,?,?,?)", (sid, name, market, tf, status, int(tf_minutes(tf) < 1440), t, t))
    else:
        c.execute("UPDATE strategies SET updated_at=? WHERE id=?", (t, sid))
    v = c.execute("SELECT COALESCE(MAX(version),0)+1 AS v FROM strategy_versions WHERE strategy_id=?", (sid,)).fetchone()["v"]
    c.execute("INSERT INTO strategy_versions (strategy_id, version, json_rules, source, metrics, note, created_at)"
              " VALUES (?,?,?,?,?,?,?)", (sid, v, jdump(rules), "lab", jdump(metrics) if metrics else None, note, t))


# ------------------------------------------------------------------------------------- variants

def _tunable(params: dict) -> dict:
    return {k: v for k, v in params.items() if k not in NON_TUNABLE and isinstance(v, (int, float)) and not isinstance(v, bool)}


def _fix(params: dict) -> dict:
    if "fast" in params and "slow" in params and params["fast"] >= params["slow"]:
        params["slow"] = params["fast"] + 5
    return params


def make_variants(recipe: dict, n: int = 10) -> list[tuple[int, dict]]:
    """n parameter sets: the recipe's own params first, then seeded jitter of x0.6..x1.4 per param."""
    base = dict(recipe.get("params", {}))
    root = zlib.crc32(str(recipe.get("id", recipe.get("name", ""))).encode())
    out = [(root, base)]
    for k in range(1, n):
        seed = (root + 7919 * k) & 0x7FFFFFFF
        rng = np.random.default_rng(seed)
        p = dict(base)
        for key, v in _tunable(base).items():
            x = v * rng.uniform(0.6, 1.4)
            p[key] = max(1, int(round(x))) if isinstance(v, int) else round(float(x), 4)
        out.append((seed, _fix(p)))
    return out


def with_params(recipe: dict, params: dict) -> dict:
    r = copy.deepcopy(recipe)
    r["params"] = params
    return r


# ---------------------------------------------------------------------------------------- core

def _ann(market: str) -> float:
    return 365.0 if info(market).get("sessions") == "24/7" else 252.0


def evaluate(recipe: dict, df: pd.DataFrame, sp: walkforward.Split, risk_pct: float, costs: dict) -> dict:
    sigs = signals.generate(recipe, df)
    res = bt.run(df, sigs, costs=costs, risk_pct=risk_pct, market=recipe.get("market"))
    t_is, t_oos = walkforward.split_trades(res.trades, sp)
    af = _ann(recipe.get("market", ""))
    eq_is = bt.equity_from_r(t_is, risk_pct, start=sp.is_start)
    eq_oos = bt.equity_from_r(t_oos, risk_pct, start=sp.oos_start)
    m_is, m_oos = bt.metrics(t_is, eq_is, af), bt.metrics(t_oos, eq_oos, af)
    return {"signals": sigs, "result": res, "is": m_is, "oos": m_oos, "eq_oos": eq_oos, "t_oos": t_oos}


def stability(recipe: dict, df: pd.DataFrame, sp, risk_pct: float, costs: dict, base_oos: float) -> dict:
    worst, rows = base_oos, []
    for key, v in _tunable(recipe.get("params", {})).items():
        for f in (0.8, 1.2):
            p = dict(recipe["params"])
            nv = v * f
            if isinstance(v, int):
                nv = int(round(nv))
                if nv == v:
                    nv = v + (1 if f > 1 else -1)
                nv = max(1, nv)
            p[key] = nv
            s = evaluate(with_params(recipe, _fix(p)), df, sp, risk_pct, costs)["oos"]["sharpe"]
            rows.append({"param": key, "factor": f, "value": nv, "sharpe_oos": s})
            worst = min(worst, s)
    ratio = (worst / base_oos) if base_oos > 0 else 0.0
    return {"worst_sharpe_oos": round(worst, 3), "ratio": round(ratio, 3), "checks": rows}


def judge(m_is: dict, m_oos: dict, extra: dict, b: dict) -> tuple[str, str | None]:
    reasons = []
    if m_oos["trades"] < b["min_trades"]:
        reasons.append("Too few trades")
    if m_oos["expectancy_r"] <= 0:
        reasons.append("Expectancy negative after costs")
    if m_oos["dd"] < -abs(b["max_dd_pct"]):
        reasons.append("Max drawdown too deep")
    if m_oos["sharpe"] < b["oos_sharpe"]:
        reasons.append("Doesn't work out-of-sample")
    primary_ok = not reasons
    robust = []
    if extra.get("decline") is not None and extra["decline"] > b["max_decline"]:
        robust.append("Sharpe collapses IS→OOS")
    if extra.get("pbo") is not None and extra["pbo"] > b["max_pbo"]:
        robust.append("Likely overfit (PBO)")
    st = extra.get("stability")
    if st is not None and (st["ratio"] < b["stability_ratio"] or st["worst_sharpe_oos"] <= 0):
        robust.append("Unstable under ±20% parameter change")
    ch = extra.get("chance")
    if ch is not None and ch["percentile"] < b["min_chance_pct"]:
        robust.append("No better than random entries")
    if primary_ok and not robust:
        return "clear", None
    sieve_ok = (m_oos["sharpe"] >= b["sieve_sharpe"] and m_oos["trades"] >= b["min_trades"]
                and m_oos["dd"] >= -abs(b["max_dd_pct"]) and m_oos["expectancy_r"] > 0)
    why = (reasons + robust)[0]
    if why == "Doesn't work out-of-sample" and m_oos["win"] < 35 and m_oos["rr"] < 1.5:
        why = "Win rate too low"
    elif why == "Doesn't work out-of-sample" and m_oos["rr"] < 0.8:
        why = "R:R too low"
    return ("sieve" if sieve_ok else "failed"), why


def run_recipe(recipe: dict, start=None, end=None, candles: pd.DataFrame | None = None, n_variants: int | None = None,
               store: bool = True, chance_runs: int | None = None, mc_runs: int | None = None,
               check_stability: bool = True) -> dict:
    """Test a recipe: n variants, walk-forward, the bar, overfitting checks. Returns a summary."""
    market, tf = norm(recipe.get("market", "BTC/USD")), recipe.get("timeframe", "1h")
    recipe = {**recipe, "market": market}
    n_variants = n_variants or int(setting("lab.variants_per_recipe", DEFAULTS))
    risk_pct = float(setting("lab.risk_pct", DEFAULTS))
    chance_runs = chance_runs if chance_runs is not None else int(setting("lab.chance_runs", DEFAULTS))
    mc_runs = mc_runs or int(setting("lab.mc_runs", DEFAULTS))
    b = bar()
    if candles is None:
        start = start or setting("lab.history_start", DEFAULTS)
        end = end or pd.Timestamp.now(tz="UTC")
        candles = candles_mod.get(market, tf, start, end)
    df = candles
    synthetic = bool(df.attrs.get("synthetic"))
    sp = walkforward.split(df.index)
    costs = bt.costs_for(market)
    if store:
        ensure()
        save_recipe(recipe)
    name = recipe.get("name", recipe.get("id", "recipe"))
    log("TEST", f"{name} · {tf} · {n_variants} variants · walk-forward {sp.mode} "
                f"(IS {sp.is_start.date()}→{sp.oos_start.date()}, OOS →{sp.end.date()})"
                + (" · SYNTHETIC data" if synthetic else ""))
    emit("agent_status", {"agent": "LAB", "status": "working", "item": name})

    runs = []
    for k, (seed, params) in enumerate(make_variants(recipe, n_variants)):
        rv = with_params(recipe, params)
        ev = evaluate(rv, df, sp, risk_pct, costs)
        runs.append({"k": k, "seed": seed, "params": params, "recipe": rv, **ev})

    # PBO across the variants, on weekly returns of the full-period equity curves
    pbo = None
    try:
        M = overfit.returns_matrix([r["result"].equity for r in runs])
        pbo = overfit.pbo_cscv(M, S=16)["pbo"] if M.shape[0] >= 32 else None
    except Exception:
        pbo = None

    out_rows = []
    for r in runs:
        m_is, m_oos = r["is"], r["oos"]
        extra = {"pbo": pbo, "decline": overfit.sharpe_decline(m_is["sharpe"], m_oos["sharpe"])}
        prelim, _ = judge(m_is, m_oos, {}, b)
        if prelim in ("clear", "sieve"):   # robustness checks only where they can change the answer
            if check_stability:
                extra["stability"] = stability(r["recipe"], df, sp, risk_pct, costs, m_oos["sharpe"])
            oos_df = df[sp.oos_mask(df.index)]
            oos_sigs = [s for s in r["signals"] if pd.Timestamp(s["time"]) >= sp.oos_start]
            if chance_runs:
                extra["chance"] = overfit.chance_score(oos_df, oos_sigs, m_oos["expectancy_r"], n_random=chance_runs,
                                                       risk_pct=risk_pct, costs=costs, market=market)
        outcome, why = judge(m_is, m_oos, extra, b)
        mc = overfit.monte_carlo_dd(r["t_oos"]["r"].to_numpy() if len(r["t_oos"]) else np.array([]),
                                    risk_pct, n=mc_runs, bad_dd_pct=-abs(b["max_dd_pct"]))
        label = f"{name} {r['k'] + 1}"
        payload = {"id": None, "recipe": label, "market": market.split("/")[0], "tf": tf,
                   "sharpeIS": round(m_is["sharpe"], 2), "sharpeOOS": round(m_oos["sharpe"], 2),
                   "trades": int(m_oos["trades"] + m_is["trades"]), "win": round(m_oos["win"], 1),
                   "rr": round(m_oos["rr"], 2), "dd": round(m_oos["dd"], 1), "outcome": outcome, "why": why,
                   "seed": int(r["seed"])}
        vid = None
        if store:
            from nsq.db import conn
            c = conn()
            cur = c.execute("INSERT INTO variants (recipe_id, label, seed, params_json, market, tf, sharpe_is, sharpe_oos, trades,"
                            " win, rr, dd, outcome, why, metrics_json, synthetic, created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                            (recipe["id"], label, r["seed"], jdump(r["params"]), market, tf, m_is["sharpe"], m_oos["sharpe"],
                             payload["trades"], m_oos["win"], m_oos["rr"], m_oos["dd"], outcome, why,
                             jdump({"is": m_is, "oos": m_oos, **{k: v for k, v in extra.items() if k != "stability"}}),
                             int(synthetic), now_ms()))
            vid = cur.lastrowid
            c.execute("INSERT INTO backtests (variant_id, recipe_id, market, tf, start, end, split_json, costs_json, metrics_is,"
                      " metrics_oos, pbo, chance_json, mc_json, stability_json, equity_json, synthetic, data_source, created_at)"
                      " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                      (vid, recipe["id"], market, tf, df.index[0].isoformat(), df.index[-1].isoformat(), jdump(sp.as_dict()),
                       jdump(costs), jdump(m_is), jdump(m_oos), pbo, jdump(extra.get("chance")), jdump(mc),
                       jdump(extra.get("stability")), jdump(bt.downsample(r["result"].equity)), int(synthetic),
                       df.attrs.get("source"), now_ms()))
        payload["id"] = vid if vid is not None else r["k"] + 1
        emit("variant_tested", payload)
        out_rows.append({**payload, "params": r["params"], "metrics_is": m_is, "metrics_oos": m_oos,
                         "equity": bt.downsample(r["result"].equity, 120), "mc": mc,
                         "stability": extra.get("stability"), "chance": extra.get("chance")})

    counts = {o: sum(1 for r in out_rows if r["outcome"] == o) for o in ("clear", "sieve", "failed")}
    best = max(out_rows, key=lambda r: r["sharpeOOS"]) if out_rows else None
    summary = {"recipe": recipe["id"] if store else recipe.get("id"), "name": name, "market": market, "tf": tf,
               "variants": len(out_rows), **counts, "pbo": pbo, "split": sp.as_dict(), "synthetic": synthetic,
               "data_source": df.attrs.get("source"), "best": {k: best[k] for k in ("id", "recipe", "sharpeIS", "sharpeOOS",
                                                                                      "trades", "outcome")} if best else None,
               "bar": b}
    emit("backtest_done", summary)
    emit("agent_status", {"agent": "LAB", "status": "idle", "item": name})
    log("TEST", f"{name} done · clear {counts['clear']} · sieve {counts['sieve']} · failed {counts['failed']}"
                + (f" · PBO {pbo:.2f}" if pbo is not None else ""))
    if store:
        from nsq.db import conn
        conn().execute("UPDATE recipes SET status=? WHERE id=?", ("cleared" if counts["clear"] else "tested", recipe["id"]))
        if counts["clear"] and best and best["outcome"] == "clear" and not synthetic:
            sid = recipe["id"]
            upsert_strategy(sid, name, market, tf, with_params(recipe, best["params"]),
                            {"is": best["metrics_is"], "oos": best["metrics_oos"], "pbo": pbo}, "cleared the bar in the Lab")
            emit("strategy_status", {"id": sid, "name": name, "status": "lab", "note": "cleared the bar"})
        audit_safe("lab", "backtest_done", {k: summary[k] for k in ("recipe", "market", "tf", "clear", "sieve", "failed", "synthetic")})
    summary["rows"] = out_rows
    return summary
