"""Interactive Brokers through a locally running IB Gateway / TWS and `ib_async` (the maintained fork of
ib_insync, BSD-2). Optional dependency: `pip install ib_async`.

Verified against the ib_async 2.1.0 source: `IB().connect(host, port, clientId)`,
`ib.bracketOrder(action, quantity, limitPrice, takeProfitPrice, stopLossPrice)` returns
BracketOrder(parent, takeProfit, stopLoss) with transmit flags set, `ib.placeOrder(contract, order)`,
`ib.positions()`, `ib.openTrades()`, `ib.cancelOrder`, `ib.reqHistoricalData`.
The parent of an IB bracket is a LIMIT order; we price it marketable (ask/bid +/- a small buffer).
Withdrawals are impossible through the TWS API, so they are reported OFF.
Default port 4002 = IB Gateway paper account.
"""
from __future__ import annotations

import pandas as pd

from .base import Account, BracketResult, BrokerAdapter, BrokerError, Order, Position

_TF = {"1m": "1 min", "5m": "5 mins", "15m": "15 mins", "30m": "30 mins", "1h": "1 hour", "4h": "4 hours", "1d": "1 day"}


class IBKRBroker(BrokerAdapter):
    name = "ibkr"
    title = "Interactive Brokers (IB Gateway)"
    status = "ready"
    native_brackets = True
    markets = ("AAPL", "NVDA", "XAU/USD", "EUR/USD")
    docs_url = "https://ib-api-reloaded.github.io/ib_async/"
    withdraw_page = "https://www.interactivebrokers.co.uk/portal/#/transfer"

    def __init__(self, host: str = "127.0.0.1", port: int = 4002, client_id: int = 17):
        try:
            import ib_async as ib
        except ImportError:
            try:
                import ib_insync as ib  # type: ignore
            except ImportError as e:
                raise BrokerError("Interactive Brokers needs: pip install ib_async, and IB Gateway running") from e
        self.lib = ib
        self.ib = ib.IB()
        self.host, self.port, self.client_id = host, port, client_id

    def _contract(self, market: str):
        if market == "XAU/USD":
            return self.lib.Commodity("XAUUSD", "SMART", "USD")
        if market == "EUR/USD":
            return self.lib.Forex("EURUSD")
        return self.lib.Stock(market, "SMART", "USD")

    def connect(self) -> bool:
        if not self.ib.isConnected():
            self.ib.connect(self.host, self.port, clientId=self.client_id, timeout=10)
        return True

    def online(self) -> bool:
        return self.ib.isConnected()

    def account(self) -> Account:
        vals = {v.tag: v for v in self.ib.accountSummary()}
        f = lambda t: float(vals[t].value) if t in vals else 0.0  # noqa: E731
        ccy = vals["NetLiquidation"].currency if "NetLiquidation" in vals else "GBP"
        return Account("ibkr", ccy, f("TotalCashValue"), f("NetLiquidation"), f("InitMarginReq"), demo=self.port in (4002, 7497))

    def positions(self) -> list[Position]:
        out = []
        trades = self.ib.openTrades()
        for p in self.ib.positions():
            sym = p.contract.symbol
            pos = Position(str(p.contract.conId), sym, "buy" if p.position > 0 else "sell", abs(p.position), p.avgCost)
            for t in trades:
                if t.contract.conId == p.contract.conId:
                    if t.order.orderType in ("STP", "STP LMT"):
                        pos.stop, pos.stop_order_id = t.order.auxPrice, str(t.order.orderId)
                    elif t.order.orderType == "LMT":
                        pos.target, pos.target_order_id = t.order.lmtPrice, str(t.order.orderId)
            out.append(pos)
        return out

    def orders(self) -> list[Order]:
        out = []
        for t in self.ib.openTrades():
            o = t.order
            px = o.auxPrice if o.orderType.startswith("STP") else o.lmtPrice
            out.append(Order(str(o.orderId), o.orderRef or "", t.contract.symbol, o.action.lower(), o.orderType.lower(),
                             o.totalQuantity, px, "open", "stop" if o.orderType.startswith("STP") else "target",
                             str(o.parentId) if o.parentId else None))
        return out

    def place_bracket(self, market, side, qty, stop, target, client_order_id, meta=None) -> BracketResult:
        for o in self.orders():
            if o.client_order_id == client_order_id:
                return BracketResult(True, None, o, None, None, idempotent_replay=True)
        c = self._contract(market)
        self.ib.qualifyContracts(c)
        [tk] = self.ib.reqTickers(c)
        ref = (tk.ask if side == "buy" else tk.bid) or tk.marketPrice()
        limit = ref * (1.001 if side == "buy" else 0.999)
        br = self.ib.bracketOrder(side.upper(), qty, round(limit, 2), round(target, 2), round(stop, 2))
        for o in br:
            o.orderRef = client_order_id
            self.ib.placeOrder(c, o)
        mk = lambda o, role, px: Order(str(o.orderId), client_order_id, market, o.action.lower(), o.orderType.lower(), qty, px,  # noqa: E731
                                       "open", role, str(o.parentId) if o.parentId else None)
        return BracketResult(True, None, mk(br.parent, "entry", limit), mk(br.stopLoss, "stop", stop),
                             mk(br.takeProfit, "target", target), None)

    def modify(self, order_id: str, price: float) -> Order:
        for t in self.ib.openTrades():
            if str(t.order.orderId) == order_id:
                if t.order.orderType.startswith("STP"):
                    t.order.auxPrice = price
                else:
                    t.order.lmtPrice = price
                self.ib.placeOrder(t.contract, t.order)
                return Order(order_id, t.order.orderRef, t.contract.symbol, t.order.action.lower(), t.order.orderType.lower(),
                             t.order.totalQuantity, price, "open")
        raise BrokerError("ibkr: order not found")

    def cancel(self, order_id: str) -> bool:
        for t in self.ib.openTrades():
            if str(t.order.orderId) == order_id:
                self.ib.cancelOrder(t.order)
                return True
        return False

    def close(self, position_id: str, qty: float | None = None) -> dict:
        for p in self.ib.positions():
            if str(p.contract.conId) == position_id:
                action = "SELL" if p.position > 0 else "BUY"
                o = self.lib.MarketOrder(action, qty or abs(p.position))
                self.ib.placeOrder(p.contract, o)
                return {"position_id": position_id, "closed_qty": qty or abs(p.position)}
        raise BrokerError("ibkr: position not found")

    def candles(self, market: str, timeframe: str = "15m", start=None, end=None) -> pd.DataFrame:
        c = self._contract(market)
        bars = self.ib.reqHistoricalData(c, endDateTime=end or "", durationStr="5 D", barSizeSetting=_TF.get(timeframe, "15 mins"),
                                         whatToShow="MIDPOINT" if market in ("EUR/USD", "XAU/USD") else "TRADES", useRTH=False)
        df = self.lib.util.df(bars)
        if df is None or df.empty:
            return pd.DataFrame()
        df.index = pd.to_datetime(df.pop("date"), utc=True)
        df = df[["open", "high", "low", "close", "volume"]]
        df.attrs.update(source="ibkr", synthetic=False)
        return df

    def permissions(self) -> dict:
        return {"trading": self.ib.isConnected(), "withdrawals": False, "detectable": True,
                "note": "The TWS/Gateway API cannot withdraw money."}
