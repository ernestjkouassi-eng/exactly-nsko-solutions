"""Built-in fallback signal generator, used only if nsq.lab.signals is not installed.

Same contract as nsq.lab.signals.generate: closed bars only. A signal at bar t (its open time is the
index) uses data up to and including bar t's close. EMA cross with an ATR stop and an R-multiple target.
"""
from __future__ import annotations

import pandas as pd


def generate(recipe: dict, candles: pd.DataFrame) -> list[dict]:
    p = {**recipe.get("entry", {}), **recipe.get("params", {})}
    fast, slow, n_atr = int(p.get("fast", 9)), int(p.get("slow", 21)), int(p.get("atr", 14))
    mult = float(recipe.get("stop", {}).get("mult", 1.0))
    r = float(recipe.get("target", {}).get("r", 1.6))
    c = candles["close"]
    ef, es = c.ewm(span=fast, adjust=False).mean(), c.ewm(span=slow, adjust=False).mean()
    tr = pd.concat([candles["high"] - candles["low"], (candles["high"] - c.shift()).abs(), (candles["low"] - c.shift()).abs()], axis=1).max(axis=1)
    atr = tr.rolling(n_atr, min_periods=n_atr).mean()
    out = []
    diff = ef - es
    for i in range(max(slow, n_atr) + 1, len(candles)):
        a = atr.iloc[i]
        if pd.isna(a) or a <= 0:
            continue
        side = 1 if diff.iloc[i - 1] <= 0 < diff.iloc[i] else -1 if diff.iloc[i - 1] >= 0 > diff.iloc[i] else 0
        if not side:
            continue
        e = float(c.iloc[i])
        st = e - side * mult * a
        out.append({"time": candles.index[i], "side": "buy" if side > 0 else "sell", "entry": e, "stop": float(st),
                    "target": float(e + side * r * mult * a), "reason": f"EMA {fast}/{slow} cross (fallback generator)"})
    return out
