"""Kraken (spot crypto). REST adapter.

Verified against: live probes of api.kraken.com (public `/0/public/Time`, `/AssetPairs`, `/OHLC` answer;
private `/0/private/Balance` answers `EAPI:Invalid key` to a bad `API-Key` header) and the
signing / AddOrder parameters as implemented in the open-source ccxt `kraken.py` (MIT).
docs.kraken.com itself was not reachable from the build machine.

Signing: API-Sign = base64(HMAC-SHA512(base64decode(secret), uri_path + SHA256(nonce + postdata))).
AddOrder: pair, type (buy|sell), ordertype (market|limit|stop-loss|take-profit|...), volume, price,
cl_ord_id, validate.

Brackets: Kraken spot has no native OCO bracket, so `native_brackets=False` and the engine fallback
runs: market entry, then a broker-side `stop-loss` order, then a `take-profit` order. Spot balances are
reserved by the first open sell order, so Kraken may reject the second exit order for "insufficient
funds". In that case the stop stays broker-side (the protection that matters) and the target is
managed by the engine (`soft_target_ok=True`): when price reaches the target the engine cancels the stop
and sells at market. Long only (no margin).

Gold: Kraken has no XAU/USD spot. PAXG/USD (a gold-backed token) is offered as a proxy and labelled so.
Permissions: Kraken has no endpoint that reports a key's permissions without touching funding
endpoints, and this engine never calls funding endpoints. So withdrawals are "not detectable":
create the key with Query + Trade permissions only and leave "Withdraw Funds" unticked.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import time
import urllib.parse

import pandas as pd

from .base import Account, BracketResult, BrokerAdapter, BrokerError, Order, Position

API = "https://api.kraken.com"
PAIRS = {"BTC/USD": "XBTUSD", "ETH/USD": "ETHUSD", "PAXG/USD": "PAXGUSD"}
ASSETS = {"BTC/USD": ("XXBT", "XBT.F"), "ETH/USD": ("XETH", "ETH.F"), "PAXG/USD": ("PAXG",)}
_TF = {"1m": 1, "5m": 5, "15m": 15, "30m": 30, "1h": 60, "4h": 240, "1d": 1440}


def sign(path: str, data: dict, secret_b64: str) -> str:
    post = urllib.parse.urlencode(data)
    sha = hashlib.sha256((str(data["nonce"]) + post).encode()).digest()
    mac = hmac.new(base64.b64decode(secret_b64), path.encode() + sha, hashlib.sha512)
    return base64.b64encode(mac.digest()).decode()


class KrakenBroker(BrokerAdapter):
    name = "kraken"
    title = "Kraken"
    status = "ready"
    native_brackets = False
    soft_target_ok = True
    markets = tuple(PAIRS)
    docs_url = "https://docs.kraken.com/api/"
    withdraw_page = "https://www.kraken.com/u/funding/withdraw"

    def __init__(self, api_key: str = "", secret: str = "", client=None):
        import httpx
        self.key, self.secret = api_key, secret
        self.http = client or httpx.Client(timeout=15)
        self._nonce = 0

    # --------------------------------------------------------------- transport
    def _public(self, method: str, params: dict | None = None) -> dict:
        r = self.http.get(f"{API}/0/public/{method}", params=params or {})
        j = r.json()
        if j.get("error"):
            raise BrokerError(f"kraken {method}: {j['error']}")
        return j["result"]

    def _private(self, method: str, data: dict | None = None) -> dict:
        if not self.key or not self.secret:
            raise BrokerError("kraken: no API key saved")
        self._nonce = max(self._nonce + 1, int(time.time() * 1000))
        data = {"nonce": self._nonce, **(data or {})}
        path = f"/0/private/{method}"
        headers = {"API-Key": self.key, "API-Sign": sign(path, data, self.secret),
                   "Content-Type": "application/x-www-form-urlencoded"}
        r = self.http.post(f"{API}{path}", content=urllib.parse.urlencode(data), headers=headers)
        j = r.json()
        if j.get("error"):
            raise BrokerError(f"kraken {method}: {j['error']}")
        return j["result"]

    # --------------------------------------------------------------- adapter
    def connect(self) -> bool:
        self._public("Time")
        if self.key:
            self._private("Balance")
        return True

    def account(self) -> Account:
        tb = self._private("TradeBalance", {"asset": "ZUSD"})
        return Account("kraken", "USD", float(tb.get("tb", 0)), float(tb.get("e", tb.get("eb", 0))), float(tb.get("m", 0)))

    def positions(self) -> list[Position]:
        bal = self._private("Balance")
        out = []
        open_orders = self.orders()
        for market, codes in ASSETS.items():
            qty = sum(float(bal.get(c, 0)) for c in codes)
            if qty <= 0:
                continue
            p = Position(f"kraken-{PAIRS[market]}", market, "buy", qty, 0.0, meta={"spot_balance": True})
            for o in open_orders:
                if o.market == market and o.side == "sell":
                    if o.kind.startswith("stop"):
                        p.stop, p.stop_order_id = o.price, o.id
                    elif o.kind.startswith("take-profit") or o.kind == "limit":
                        p.target, p.target_order_id = o.price, o.id
            out.append(p)
        return out

    def orders(self) -> list[Order]:
        res = self._private("OpenOrders").get("open", {})
        inv = {v: k for k, v in PAIRS.items()}
        out = []
        for txid, o in res.items():
            d = o.get("descr", {})
            market = inv.get(d.get("pair", "").replace("/", ""), d.get("pair", ""))
            price = float(d.get("price") or 0) or None
            out.append(Order(txid, str(o.get("cl_ord_id") or o.get("userref") or ""), market, d.get("type", ""),
                             d.get("ordertype", ""), float(o.get("vol", 0)), price, "open"))
        return out

    def place_bracket(self, *a, **k) -> BracketResult:
        raise BrokerError("kraken spot has no native bracket orders: the engine fallback places the legs")

    def place_order(self, market, side, qty, kind, price, client_order_id, role="entry", position_id=None) -> Order:
        if market not in PAIRS:
            raise BrokerError(f"kraken: {market} not supported")
        ordertype = {"entry": "market", "stop": "stop-loss", "target": "take-profit", "exit": "market"}[role]
        data = {"pair": PAIRS[market], "type": side, "ordertype": ordertype, "volume": f"{qty:.8f}",
                "cl_ord_id": client_order_id}
        if role in ("stop", "target"):
            data["price"] = f"{price:.2f}"
        r = self._private("AddOrder", data)
        txid = (r.get("txid") or [client_order_id])[0]
        return Order(txid, client_order_id, market, side, ordertype, qty, price, "filled" if role == "entry" else "open", role)

    def modify(self, order_id: str, price: float) -> Order:
        r = self._private("AmendOrder", {"txid": order_id, "trigger_price": f"{price:.2f}"})
        return Order(r.get("amend_id", order_id), "", "", "", "amend", 0, price, "open")

    def cancel(self, order_id: str) -> bool:
        self._private("CancelOrder", {"txid": order_id})
        return True

    def close(self, position_id: str, qty: float | None = None) -> dict:
        p = next((p for p in self.positions() if p.id == position_id), None)
        if not p:
            raise BrokerError("kraken: position not found")
        for oid in (p.stop_order_id, p.target_order_id):
            if oid:
                self.cancel(oid)
        o = self.place_order(p.market, "sell", qty or p.qty, "market", None, f"x{int(time.time() * 1000)}", "exit")
        return {"position_id": position_id, "order": o.id, "closed_qty": qty or p.qty}

    def candles(self, market: str, timeframe: str = "15m", start=None, end=None) -> pd.DataFrame:
        params = {"pair": PAIRS.get(market, market), "interval": _TF.get(timeframe, 15)}
        if start is not None:
            params["since"] = int(pd.Timestamp(start).timestamp())
        res = self._public("OHLC", params)
        rows = next(v for k, v in res.items() if k != "last")
        df = pd.DataFrame(rows, columns=["time", "open", "high", "low", "close", "vwap", "volume", "count"])
        df.index = pd.to_datetime(df.pop("time"), unit="s", utc=True)
        df = df[["open", "high", "low", "close", "volume"]].astype(float)
        if end is not None:
            df = df[df.index <= pd.Timestamp(end, tz="UTC") if pd.Timestamp(end).tzinfo is None else df.index <= pd.Timestamp(end)]
        df.attrs.update(source="kraken", synthetic=False)
        return df

    def ticks(self, market: str) -> dict:
        res = self._public("Ticker", {"pair": PAIRS.get(market, market)})
        t = next(iter(res.values()))
        bid, ask = float(t["b"][0]), float(t["a"][0])
        return {"market": market, "bid": bid, "ask": ask, "price": (bid + ask) / 2, "ts": time.time()}

    def permissions(self) -> dict:
        trading = None
        try:
            self._private("OpenOrders")
            trading = True
        except BrokerError:
            trading = False
        return {"trading": trading, "withdrawals": None, "detectable": False,
                "note": "Kraken cannot report key permissions safely. Make sure 'Withdraw Funds' is NOT ticked on this key."}
