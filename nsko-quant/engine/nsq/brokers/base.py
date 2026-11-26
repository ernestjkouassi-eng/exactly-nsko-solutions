"""BrokerAdapter interface and shared types.

Every adapter implements: connect, account, positions, orders, place_bracket, modify, cancel, close,
candles, ticks, stream. Adapters also report `permissions()` (trading on, withdrawals off where
detectable) and `withdraw_url()` (the broker's own withdrawal page). THERE IS NO WITHDRAWAL CODE.
"""
from __future__ import annotations

import abc
import math
from dataclasses import asdict, dataclass, field
from typing import Any, Callable, Iterator


@dataclass
class MarketSpec:
    """Per-market trading costs and sizing (used by the paper broker and the sizer)."""
    symbol: str
    contract_size: float       # units per 1.0 of size
    qty_step: float            # broker's minimum size step
    min_qty: float
    tick_size: float
    spread: float              # typical spread in price points
    slippage: float            # typical slippage in price points (adverse, market/stop orders)
    commission_per_qty: float = 0.0   # account ccy per 1.0 of size per side
    commission_pct: float = 0.0       # % of notional per side
    quote_ccy: str = "USD"
    session: str = "24x5"             # 24x7 | 24x5 | us_equity


# Approximate retail costs. Paper numbers, not a quote from any broker.
MARKETS: dict[str, MarketSpec] = {
    "XAU/USD": MarketSpec("XAU/USD", 100, 0.01, 0.01, 0.01, 0.30, 0.05, 0.0, 0.0, "USD", "24x5"),
    "BTC/USD": MarketSpec("BTC/USD", 1, 0.0001, 0.0001, 0.1, 15.0, 5.0, 0.0, 0.10, "USD", "24x7"),
    "ETH/USD": MarketSpec("ETH/USD", 1, 0.001, 0.001, 0.01, 1.2, 0.4, 0.0, 0.10, "USD", "24x7"),
    "EUR/USD": MarketSpec("EUR/USD", 100000, 0.01, 0.01, 0.00001, 0.00008, 0.00002, 3.0, 0.0, "USD", "24x5"),
    "NVDA": MarketSpec("NVDA", 1, 1, 1, 0.01, 0.02, 0.01, 0.0, 0.0, "USD", "us_equity"),
    "AAPL": MarketSpec("AAPL", 1, 1, 1, 0.01, 0.02, 0.01, 0.0, 0.0, "USD", "us_equity"),
}

DEFAULT_FX = {"USD": 0.79, "GBP": 1.0, "EUR": 0.85}  # to GBP, approximate; settings key fx.<CCY>


def spec(market: str) -> MarketSpec:
    if market in MARKETS:
        return MARKETS[market]
    return MarketSpec(market, 1, 0.01, 0.01, 0.01, 0.0, 0.0)


def fx_to_account(ccy: str) -> float:
    try:
        from ..settings import get
        return float(get(f"fx.{ccy}", DEFAULT_FX.get(ccy, 1.0)))
    except Exception:
        return DEFAULT_FX.get(ccy, 1.0)


def value_per_point(market: str) -> float:
    """Account-currency (GBP) value of a 1.0 price move for 1.0 of size."""
    s = spec(market)
    return s.contract_size * fx_to_account(s.quote_ccy)


def round_down(qty: float, step: float) -> float:
    if step <= 0:
        return qty
    n = math.floor(qty / step + 1e-9)
    decimals = max(0, -int(math.floor(math.log10(step)))) if step < 1 else 0
    return round(n * step, decimals + 2)


@dataclass
class Account:
    broker: str
    currency: str
    balance: float
    equity: float
    margin_used: float
    demo: bool = False
    paper: bool = False

    def dict(self) -> dict:
        return asdict(self)


@dataclass
class Order:
    id: str
    client_order_id: str
    market: str
    side: str            # buy | sell
    kind: str            # market | limit | stop
    qty: float
    price: float | None
    status: str          # open | filled | cancelled | rejected
    role: str = "entry"  # entry | stop | target | exit
    parent_id: str | None = None
    position_id: str | None = None

    def dict(self) -> dict:
        return asdict(self)


@dataclass
class Position:
    id: str
    market: str
    side: str            # buy (long) | sell (short)
    qty: float
    entry: float
    stop: float | None = None
    target: float | None = None
    stop_order_id: str | None = None
    target_order_id: str | None = None
    unrealised: float = 0.0
    realised: float = 0.0
    opened_at: float = 0.0
    meta: dict = field(default_factory=dict)

    def dict(self) -> dict:
        return asdict(self)


@dataclass
class BracketResult:
    ok: bool
    position: Position | None
    entry_order: Order | None
    stop_order: Order | None
    target_order: Order | None
    fill_price: float | None = None
    commission: float = 0.0
    error: str | None = None
    idempotent_replay: bool = False


class BrokerError(Exception):
    pass


class BrokerAdapter(abc.ABC):
    name: str = "base"
    title: str = "Base"
    status: str = "ready"          # ready | coming_soon | unsupported
    status_reason: str = ""
    native_brackets: bool = True
    markets: tuple[str, ...] = ()
    docs_url: str = ""
    withdraw_page: str = ""

    # --- lifecycle -------------------------------------------------------
    @abc.abstractmethod
    def connect(self) -> bool: ...

    def online(self) -> bool:
        return True

    # --- reads ------------------------------------------------------------
    @abc.abstractmethod
    def account(self) -> Account: ...

    @abc.abstractmethod
    def positions(self) -> list[Position]: ...

    @abc.abstractmethod
    def orders(self) -> list[Order]: ...

    # --- trading ----------------------------------------------------------
    @abc.abstractmethod
    def place_bracket(self, market: str, side: str, qty: float, stop: float, target: float,
                      client_order_id: str) -> BracketResult: ...

    def place_order(self, market: str, side: str, qty: float, kind: str, price: float | None,
                    client_order_id: str, role: str = "entry", position_id: str | None = None) -> Order:
        """Single order (used by the no-native-bracket fallback). Override where supported."""
        raise BrokerError(f"{self.name}: single orders not supported")

    @abc.abstractmethod
    def modify(self, order_id: str, price: float) -> Order: ...

    @abc.abstractmethod
    def cancel(self, order_id: str) -> bool: ...

    @abc.abstractmethod
    def close(self, position_id: str, qty: float | None = None) -> dict: ...

    # --- data -------------------------------------------------------------
    @abc.abstractmethod
    def candles(self, market: str, timeframe: str, start: Any = None, end: Any = None): ...

    def ticks(self, market: str) -> dict:
        """Latest quote {market, bid, ask, price, ts}."""
        raise BrokerError(f"{self.name}: ticks not supported")

    def stream(self, markets: list[str], on_event: Callable[[dict], None]) -> Callable[[], None]:
        """Subscribe to live quotes. Returns a stop function. Default: no stream (poll ticks)."""
        return lambda: None

    # --- safety -----------------------------------------------------------
    def permissions(self) -> dict:
        return {"trading": None, "withdrawals": None, "detectable": False,
                "note": "Create the API key with trading permission only. Never tick withdrawals."}

    def withdraw_url(self) -> str:
        return self.withdraw_page

    def info(self) -> dict:
        return {"name": self.name, "title": self.title, "status": self.status, "reason": self.status_reason,
                "native_brackets": self.native_brackets, "markets": list(self.markets), "docs": self.docs_url,
                "withdraw_page": self.withdraw_page}


class ComingSoon(BrokerAdapter):
    """Placeholder for brokers we could not verify. Every trading call refuses."""
    status = "coming_soon"

    def _no(self, *a, **k):
        raise BrokerError(f"{self.title} is coming soon: {self.status_reason}")

    connect = account = positions = orders = place_bracket = modify = cancel = close = candles = _no  # type: ignore


Stream = Iterator[dict]
