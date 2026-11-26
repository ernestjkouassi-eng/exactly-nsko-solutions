"""Forecast: N possible paths (default 1000). Rule: at least X% (default 55%) agree with the trade direction
at the horizon.

Kronos (shiyu-coder/Kronos, MIT) is used only if it is installed (its repo exposes `model.Kronos`,
`model.KronosTokenizer`, `model.KronosPredictor`). Otherwise the engine uses
`block_bootstrap_fallback`, which is clearly named in every result ("engine": "block-bootstrap fallback").
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from ..settings import get
from .paths import bar_moves, bootstrap, price_paths


def _kronos():
    try:
        from model import KronosPredictor, Kronos, KronosTokenizer  # type: ignore  # noqa: F401
        return KronosPredictor, Kronos, KronosTokenizer
    except Exception:
        return None


def kronos_available() -> bool:
    return _kronos() is not None


def _kronos_paths(df: pd.DataFrame, n: int, horizon: int) -> np.ndarray | None:
    k = _kronos()
    if not k:
        return None
    KronosPredictor, Kronos, KronosTokenizer = k
    try:
        tok = KronosTokenizer.from_pretrained("NeoQuasar/Kronos-Tokenizer-base")
        mdl = Kronos.from_pretrained("NeoQuasar/Kronos-small")
        pred = KronosPredictor(mdl, tok, max_context=512)
        x = df[["open", "high", "low", "close", "volume"]].tail(400).reset_index(drop=True)
        xt = pd.Series(df.index[-len(x):])
        step = df.index[-1] - df.index[-2]
        yt = pd.Series(pd.date_range(df.index[-1] + step, periods=horizon, freq=step))
        out = []
        for _ in range(min(n, 64)):   # Kronos sampling is slow on CPU; cap and resample
            p = pred.predict(df=x, x_timestamp=xt, y_timestamp=yt, pred_len=horizon, T=1.0, top_p=0.9, sample_count=1)
            out.append(p["close"].to_numpy())
        arr = np.array(out)
        reps = -(-n // len(arr))
        return np.tile(arr, (reps, 1))[:n]
    except Exception:
        return None


def block_bootstrap_fallback(df: pd.DataFrame, n: int, horizon: int, block: int = 8, seed: int = 0) -> np.ndarray:
    moves = bar_moves(df.tail(500))
    close, _, _ = price_paths(float(df["close"].iloc[-1]), bootstrap(moves, n, horizon, block, seed))
    return close


def forecast(df: pd.DataFrame, side: str, entry: float | None = None, n: int | None = None, horizon: int | None = None,
             agree_pct: float | None = None, seed: int = 0) -> dict:
    """df must hold CLOSED bars only (the caller drops the forming bar)."""
    n = int(n or get("forecast.paths"))
    horizon = int(horizon or get("forecast.horizon_bars"))
    need = float(agree_pct if agree_pct is not None else get("forecast.agree_pct"))
    entry = float(entry if entry is not None else df["close"].iloc[-1])
    paths = _kronos_paths(df, n, horizon)
    engine = "kronos"
    if paths is None:
        paths = block_bootstrap_fallback(df, n, horizon, seed=seed)
        engine = "block-bootstrap fallback"
    final = paths[:, -1]
    up = float((final > entry).mean() * 100)
    agree = up if side == "buy" else 100 - up
    q = np.percentile(paths, [10, 50, 90], axis=0)
    return {"engine": engine, "paths": n, "horizon_bars": horizon, "agree_pct": round(agree, 1), "need_pct": need,
            "passed": agree >= need, "side": side, "entry": entry,
            "fan": {"p10": q[0].round(6).tolist(), "p50": q[1].round(6).tolist(), "p90": q[2].round(6).tolist()},
            "sample": paths[:20].round(6).tolist()}
