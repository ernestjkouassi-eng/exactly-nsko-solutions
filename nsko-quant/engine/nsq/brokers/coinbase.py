"""Coinbase Advanced Trade (spot crypto), through Coinbase's official SDK `coinbase-advanced-py` (optional dep).

Verified against the SDK 1.8.4 source: `RESTClient(api_key, api_secret)` signs requests with a CDP JWT;
`market_order_buy/sell(client_order_id, product_id, base_size)`, `trigger_bracket_order_gtc(client_order_id,
product_id, side, base_size, limit_price, stop_trigger_price)` (an exit bracket on a holding: take-profit
limit + stop trigger, one cancels the other), `list_orders`, `cancel_orders`, `get_candles`,
`get_api_key_permissions` (returns can_view / can_trade / can_transfer). Endpoints under
https://api.coinbase.com/api/v3/brokerage/.

Brackets: no entry+exit bracket in one call, so `native_brackets=False`: the engine's fallback buys at
market, then attaches the exit bracket (stop + target in one OCO order) and verifies it. Long only.
Permissions: detectable. If the key can transfer funds the engine refuses to trade with it.
The SDK is not installed by default; `pip install coinbase-advanced-py` enables this adapter.
"""
from __future__ import annotations

import time

import pandas as pd

from .base import Account, BracketResult, BrokerAdapter, BrokerError, Order, Position

PRODUCTS = {"BTC/USD": "BTC-USD", "ETH/USD": "ETH-USD"}
_TF = {"1m": "ONE_MINUTE", "5m": "FIVE_MINUTE", "15m": "FIFTEEN_MINUTE", "30m": "THIRTY_MINUTE",
       "1h": "ONE_HOUR", "1d": "ONE_DAY"}  # 4h: not confirmed in the SDK source, so not offered


def _d(x):
    return x.to_dict() if hasattr(x, "to_dict") else x


class CoinbaseBroker(BrokerAdapter):
    name = "coinbase"
    title = "Coinbase Advanced"
    status = "ready"
    native_brackets = False
    exit_bracket = True        # stop and target go on as ONE OCO exit order
    markets = tuple(PRODUCTS)
    docs_url = "https://docs.cdp.coinbase.com/advanced-trade/docs/welcome"
    withdraw_page = "https://www.coinbase.com/settings"

    def __init__(self, api_key: str, api_secret: str, client=None):
        if client is None:
            try:
                from coinbase.rest import RESTClient
            except ImportError as e:
                raise BrokerError("Coinbase needs the official SDK: pip install coinbase-advanced-py") from e
            client = RESTClient(api_key=api_key, api_secret=api_secret)
        self.c = client

    def connect(self) -> bool:
        perms = self.permissions()
        if perms.get("withdrawals"):
            raise BrokerError("This Coinbase key can transfer funds. Make a new key with View + Trade only.")
        return True

    def account(self) -> Account:
        accts = _d(self.c.get_accounts()).get("accounts", [])
        usd = sum(float(a["available_balance"]["value"]) for a in accts if a.get("currency") in ("USD", "USDC"))
        return Account("coinbase", "USD", usd, usd, 0.0)

    def positions(self) -> list[Position]:
        accts = _d(self.c.get_accounts()).get("accounts", [])
        inv = {v.split("-")[0]: k for k, v in PRODUCTS.items()}
        out = []
        for a in accts:
            m = inv.get(a.get("currency"))
            qty = float(a.get("available_balance", {}).get("value", 0)) + float(a.get("hold", {}).get("value", 0))
            if m and qty > 0:
                out.append(Position(f"coinbase-{a['currency']}", m, "buy", qty, 0.0, meta={"spot_balance": True}))
        for o in self.orders():
            for p in out:
                if p.market == o.market and o.kind == "trigger_bracket_gtc":
                    p.stop, p.target = o.meta_stop, o.price  # type: ignore[attr-defined]
                    p.stop_order_id = p.target_order_id = o.id
        return out

    def orders(self) -> list[Order]:
        res = _d(self.c.list_orders(order_status=["OPEN"])).get("orders", [])
        inv = {v: k for k, v in PRODUCTS.items()}
        out = []
        for o in res:
            cfg = o.get("order_configuration", {})
            kind = next(iter(cfg), "unknown")
            c = cfg.get(kind, {})
            od = Order(o["order_id"], o.get("client_order_id", ""), inv.get(o["product_id"], o["product_id"]),
                       o["side"].lower(), kind, float(c.get("base_size", 0) or 0),
                       float(c["limit_price"]) if c.get("limit_price") else None, "open",
                       "target" if kind == "trigger_bracket_gtc" else "entry")
            od.meta_stop = float(c["stop_trigger_price"]) if c.get("stop_trigger_price") else None  # type: ignore[attr-defined]
            out.append(od)
        return out

    def place_bracket(self, *a, **k) -> BracketResult:
        raise BrokerError("coinbase: entry and exit bracket are separate orders; the engine fallback places them")

    def place_order(self, market, side, qty, kind, price, client_order_id, role="entry", position_id=None, stop=None) -> Order:
        pid = PRODUCTS[market]
        if role == "entry":
            fn = self.c.market_order_buy if side == "buy" else self.c.market_order_sell
            r = _d(fn(client_order_id=client_order_id, product_id=pid, base_size=f"{qty:.8f}"))
            oid = r.get("success_response", {}).get("order_id") or r.get("order_id", client_order_id)
            return Order(oid, client_order_id, market, side, "market", qty, None, "filled", "entry")
        raise BrokerError("coinbase: use place_exit_bracket for the stop and target")

    def place_exit_bracket(self, market, qty, stop, target, client_order_id) -> Order:
        r = _d(self.c.trigger_bracket_order_gtc(client_order_id=client_order_id, product_id=PRODUCTS[market], side="SELL",
                                                 base_size=f"{qty:.8f}", limit_price=f"{target:.2f}",
                                                 stop_trigger_price=f"{stop:.2f}"))
        if not r.get("success", True):
            raise BrokerError(f"coinbase exit bracket rejected: {r.get('error_response')}")
        oid = r.get("success_response", {}).get("order_id", client_order_id)
        return Order(oid, client_order_id, market, "sell", "trigger_bracket_gtc", qty, target, "open", "target")

    def modify(self, order_id: str, price: float) -> Order:
        raise BrokerError("coinbase: cancel and re-place the exit bracket to move it")

    def cancel(self, order_id: str) -> bool:
        self.c.cancel_orders(order_ids=[order_id])
        return True

    def close(self, position_id: str, qty: float | None = None) -> dict:
        p = next((p for p in self.positions() if p.id == position_id), None)
        if not p:
            raise BrokerError("coinbase: position not found")
        if p.stop_order_id:
            self.cancel(p.stop_order_id)
        r = _d(self.c.market_order_sell(client_order_id=f"x{int(time.time() * 1000)}", product_id=PRODUCTS[p.market],
                                        base_size=f"{(qty or p.qty):.8f}"))
        return {"position_id": position_id, "closed_qty": qty or p.qty, "order": r.get("success_response", {}).get("order_id")}

    def candles(self, market: str, timeframe: str = "15m", start=None, end=None) -> pd.DataFrame:
        end = pd.Timestamp(end or pd.Timestamp.now(tz="UTC"))
        start = pd.Timestamp(start or end - pd.Timedelta(days=3))
        r = _d(self.c.get_candles(product_id=PRODUCTS[market], start=str(int(start.timestamp())),
                                  end=str(int(end.timestamp())), granularity=_TF.get(timeframe, "FIFTEEN_MINUTE")))
        df = pd.DataFrame(r.get("candles", []))
        if df.empty:
            return df
        df.index = pd.to_datetime(df.pop("start").astype(int), unit="s", utc=True)
        df = df[["open", "high", "low", "close", "volume"]].astype(float).sort_index()
        df.attrs.update(source="coinbase", synthetic=False)
        return df

    def permissions(self) -> dict:
        p = _d(self.c.get_api_key_permissions())
        return {"trading": bool(p.get("can_trade")), "withdrawals": bool(p.get("can_transfer")), "detectable": True,
                "note": "Coinbase reports key permissions. Transfer permission must be OFF."}
