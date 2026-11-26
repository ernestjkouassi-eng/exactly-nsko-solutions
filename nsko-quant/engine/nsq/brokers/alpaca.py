"""Alpaca (US stocks and crypto). REST adapter.

Verified against: Alpaca's official Python SDK `alpaca-py` 0.45 source (order request fields,
endpoints) and live probes of paper-api.alpaca.markets / data.alpaca.markets (auth headers
`APCA-API-KEY-ID` / `APCA-API-SECRET-KEY`, `/v2/account` answers 401 without keys,
`/v1beta3/crypto/us/bars` answers publicly). docs.alpaca.markets itself was not reachable from the
build machine.

- Trading base: https://paper-api.alpaca.markets (default, free paper account) or https://api.alpaca.markets (live).
- Brackets: native `order_class="bracket"` with `take_profit.limit_price` and `stop_loss.stop_price`
  (US equities, whole shares). Crypto orders are simple only, so crypto uses the engine fallback
  (entry, then stop and target orders, verified).
- Permissions: Alpaca trading API keys cannot move money out (transfers are not part of the Trading
  API), so withdrawals are reported OFF.
"""
from __future__ import annotations

import pandas as pd

from .base import Account, BracketResult, BrokerAdapter, BrokerError, Order, Position

PAPER = "https://paper-api.alpaca.markets"
LIVE = "https://api.alpaca.markets"
DATA = "https://data.alpaca.markets"
_TF = {"1m": "1Min", "5m": "5Min", "15m": "15Min", "30m": "30Min", "1h": "1Hour", "4h": "4Hour", "1d": "1Day"}


def _sym(market: str) -> str:
    return market  # Alpaca uses "AAPL" and "BTC/USD" as-is


class AlpacaBroker(BrokerAdapter):
    name = "alpaca"
    title = "Alpaca"
    status = "ready"
    native_brackets = True
    markets = ("AAPL", "NVDA", "BTC/USD", "ETH/USD")
    docs_url = "https://docs.alpaca.markets/"
    withdraw_page = "https://app.alpaca.markets/brokerage/banking"

    def __init__(self, key_id: str, secret: str, live: bool = False, client=None):
        import httpx
        self.base = LIVE if live else PAPER
        self.live = live
        h = {"APCA-API-KEY-ID": key_id, "APCA-API-SECRET-KEY": secret}
        self.http = client or httpx.Client(timeout=15, headers=h)
        self._h = h

    def _req(self, method: str, url: str, **kw):
        r = self.http.request(method, url, headers=self._h, **kw)
        if r.status_code >= 400:
            raise BrokerError(f"alpaca {method} {url.split('.markets')[-1]} -> {r.status_code}: {r.text[:200]}")
        return r.json() if r.content else {}

    def connect(self) -> bool:
        self._req("GET", f"{self.base}/v2/account")
        return True

    def account(self) -> Account:
        a = self._req("GET", f"{self.base}/v2/account")
        equity = float(a.get("equity", 0))
        return Account("alpaca", a.get("currency", "USD"), float(a.get("cash", 0)), equity,
                       float(a.get("initial_margin", 0) or 0), demo=not self.live)

    def positions(self) -> list[Position]:
        out = []
        for p in self._req("GET", f"{self.base}/v2/positions"):
            qty = float(p["qty"])
            out.append(Position(p.get("asset_id", p["symbol"]), p["symbol"], "buy" if qty > 0 else "sell", abs(qty),
                                float(p["avg_entry_price"]), unrealised=float(p.get("unrealized_pl", 0) or 0),
                                meta={"symbol": p["symbol"]}))
        # attach resting stop / target orders
        for o in self.orders():
            for p in out:
                if p.market == o.market:
                    if o.kind in ("stop", "stop_limit"):
                        p.stop, p.stop_order_id = o.price, o.id
                    elif o.kind == "limit":
                        p.target, p.target_order_id = o.price, o.id
        return out

    @staticmethod
    def _order(o: dict, role: str = "entry") -> Order:
        kind = o.get("type") or o.get("order_type") or "market"
        price = o.get("stop_price") if kind in ("stop", "stop_limit") else o.get("limit_price")
        st = o.get("status", "")
        status = "filled" if st == "filled" else "cancelled" if st in ("canceled", "expired", "rejected") else "open"
        return Order(o["id"], o.get("client_order_id", ""), o["symbol"], o["side"], kind, float(o.get("qty") or 0),
                     float(price) if price else None, status, role, o.get("parent_order_id"))

    def orders(self) -> list[Order]:
        out = []
        for o in self._req("GET", f"{self.base}/v2/orders", params={"status": "open", "nested": "true"}):
            out.append(self._order(o))
            for leg in o.get("legs") or []:
                out.append(self._order(leg, "stop" if leg.get("type") in ("stop", "stop_limit") else "target"))
        return out

    def _existing(self, cid: str) -> dict | None:
        try:
            return self._req("GET", f"{self.base}/v2/orders:by_client_order_id", params={"client_order_id": cid})
        except BrokerError:
            return None

    def place_bracket(self, market, side, qty, stop, target, client_order_id, meta=None) -> BracketResult:
        if "/" in market:
            raise BrokerError("alpaca crypto has no bracket orders: use the fallback path")
        prev = self._existing(client_order_id)   # idempotent retry
        o = prev or self._req("POST", f"{self.base}/v2/orders", json={
            "symbol": _sym(market), "qty": str(int(qty)), "side": side, "type": "market", "time_in_force": "gtc",
            "order_class": "bracket", "client_order_id": client_order_id,
            "take_profit": {"limit_price": str(round(target, 2))}, "stop_loss": {"stop_price": str(round(stop, 2))}})
        legs = o.get("legs") or []
        so = next((self._order(l, "stop") for l in legs if l.get("type") in ("stop", "stop_limit")), None)
        to = next((self._order(l, "target") for l in legs if l.get("type") == "limit"), None)
        fp = float(o["filled_avg_price"]) if o.get("filled_avg_price") else None
        pos = Position(o["id"], market, side, float(qty), fp or 0.0, stop, target, so.id if so else None, to.id if to else None)
        return BracketResult(True, pos, self._order(o), so, to, fp, idempotent_replay=prev is not None)

    def place_order(self, market, side, qty, kind, price, client_order_id, role="entry", position_id=None) -> Order:
        prev = self._existing(client_order_id)
        if prev:
            return self._order(prev, role)
        body = {"symbol": _sym(market), "qty": str(qty), "side": side, "client_order_id": client_order_id,
                "time_in_force": "gtc", "type": {"entry": "market", "stop": "stop", "target": "limit"}.get(role, kind)}
        if body["type"] == "stop":
            body["stop_price"] = str(price)
        elif body["type"] == "limit":
            body["limit_price"] = str(price)
        return self._order(self._req("POST", f"{self.base}/v2/orders", json=body), role)

    def modify(self, order_id: str, price: float) -> Order:
        cur = self._req("GET", f"{self.base}/v2/orders/{order_id}")
        field = "stop_price" if cur.get("type") in ("stop", "stop_limit") else "limit_price"
        return self._order(self._req("PATCH", f"{self.base}/v2/orders/{order_id}", json={field: str(price)}))

    def cancel(self, order_id: str) -> bool:
        self._req("DELETE", f"{self.base}/v2/orders/{order_id}")
        return True

    def close(self, position_id: str, qty: float | None = None) -> dict:
        # Alpaca closes by symbol (or asset id): DELETE /v2/positions/{symbol_or_asset_id}?qty=
        params = {"qty": str(qty)} if qty else None
        r = self._req("DELETE", f"{self.base}/v2/positions/{position_id.replace('/', '')}", params=params)
        return {"position_id": position_id, "order": r.get("id"), "closed_qty": qty}

    def candles(self, market: str, timeframe: str = "15m", start=None, end=None) -> pd.DataFrame:
        params = {"timeframe": _TF.get(timeframe, "15Min"), "limit": 1000}
        if start is not None:
            params["start"] = pd.Timestamp(start).isoformat()
        if end is not None:
            params["end"] = pd.Timestamp(end).isoformat()
        if "/" in market:
            params["symbols"] = market
            bars = self._req("GET", f"{DATA}/v1beta3/crypto/us/bars", params=params).get("bars", {}).get(market, [])
        else:
            bars = self._req("GET", f"{DATA}/v2/stocks/{market}/bars", params=params).get("bars", []) or []
        df = pd.DataFrame([{"time": b["t"], "open": b["o"], "high": b["h"], "low": b["l"], "close": b["c"], "volume": b["v"]}
                           for b in bars])
        if df.empty:
            return df
        df.index = pd.to_datetime(df.pop("time"), utc=True)
        df.attrs.update(source="alpaca", synthetic=False)
        return df

    def ticks(self, market: str) -> dict:
        if "/" in market:
            q = self._req("GET", f"{DATA}/v1beta3/crypto/us/latest/quotes", params={"symbols": market})["quotes"][market]
        else:
            q = self._req("GET", f"{DATA}/v2/stocks/quotes/latest", params={"symbols": market})["quotes"][market]
        bid, ask = float(q["bp"]), float(q["ap"])
        return {"market": market, "bid": bid, "ask": ask, "price": (bid + ask) / 2, "ts": q.get("t")}

    def permissions(self) -> dict:
        try:
            a = self._req("GET", f"{self.base}/v2/account")
            trading = not a.get("trading_blocked", False) and not a.get("account_blocked", False)
        except BrokerError:
            trading = None
        return {"trading": trading, "withdrawals": False, "detectable": True,
                "note": "Alpaca trading keys cannot move money out of the account."}
