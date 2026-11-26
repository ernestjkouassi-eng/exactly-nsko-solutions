import os
import sys
from pathlib import Path

os.environ["NSQ_FAST_KDF"] = "1"          # quick Argon2 parameters, tests only
os.environ["NSQ_VAULT_BACKEND"] = "file"   # never touch the developer's real keychain
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import pytest  # noqa: E402


@pytest.fixture(autouse=True)
def fresh(tmp_path, monkeypatch):
    monkeypatch.setenv("NSQ_DATA", str(tmp_path))
    from nsq import account, bus, connectivity, db, notify
    from nsq.brokers import set_active
    db.reset_for_tests()
    bus.clear_recent()
    account._reset_for_tests()
    connectivity.force(None)
    set_active(None)
    notify._sent.clear()
    from nsq.settings import set as sset
    sset("news.use_data_calendar", False)   # deterministic: only events the test adds
    yield tmp_path
    connectivity.force(None)
    set_active(None)
    db.reset_for_tests()


def trend_candles(market="XAU/USD", n=400, tf_min=15, drift=0.0006, vol=0.0012, seed=3, end=None):
    """Synthetic, seeded, closed bars with a gentle up-trend."""
    rng = np.random.default_rng(seed)
    px0 = 2648.4
    rets = rng.normal(drift, vol, n)
    close = px0 * np.exp(np.cumsum(rets))
    open_ = np.concatenate([[px0], close[:-1]])
    wig = np.abs(rng.normal(0, vol / 3, n)) * close
    high = np.maximum(open_, close) + wig
    low = np.minimum(open_, close) - wig
    end = end or pd.Timestamp("2026-11-24 10:00", tz="UTC")
    idx = pd.date_range(end=end, periods=n, freq=f"{tf_min}min", tz="UTC")
    df = pd.DataFrame({"open": open_, "high": high, "low": low, "close": close, "volume": rng.lognormal(5, .5, n)}, index=idx)
    df.attrs["synthetic"] = True
    return df


@pytest.fixture
def candles():
    return trend_candles()


@pytest.fixture
def paper():
    from nsq.brokers import set_active
    from nsq.brokers.paper import PaperBroker
    b = PaperBroker(start_balance=10000.0)
    b.set_price("XAU/USD", 2650.0)
    set_active(b)
    return b
