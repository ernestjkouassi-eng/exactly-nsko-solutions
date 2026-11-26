"""Real adapters against mocked HTTP (no keys needed): request shapes match the verified APIs."""
import base64
import hashlib
import hmac
import json
import urllib.parse

import httpx

from nsq.brokers.alpaca import AlpacaBroker
from nsq.brokers.kraken import KrakenBroker, sign


def test_kraken_signature_matches_spec():
    secret = base64.b64encode(b"k" * 64).decode()
    data = {"nonce": 1616492376594, "ordertype": "limit", "pair": "XBTUSD", "price": 37500, "type": "buy", "volume": 1.25}
    post = urllib.parse.urlencode(data)
    expect = base64.b64encode(hmac.new(base64.b64decode(secret), b"/0/private/AddOrder" +
                                       hashlib.sha256((str(data["nonce"]) + post).encode()).digest(), hashlib.sha512).digest()).decode()
    assert sign("/0/private/AddOrder", data, secret) == expect


def test_kraken_add_order_request():
    seen = {}

    def handler(req: httpx.Request):
        seen["path"], seen["headers"], seen["body"] = req.url.path, req.headers, urllib.parse.parse_qs(req.content.decode())
        return httpx.Response(200, json={"error": [], "result": {"txid": ["OABC-123"]}})
    k = KrakenBroker("KEY", base64.b64encode(b"s" * 64).decode(), client=httpx.Client(transport=httpx.MockTransport(handler)))
    o = k.place_order("BTC/USD", "sell", 0.01, "stop", 60000.0, "nsq-x-SL", role="stop")
    assert seen["path"] == "/0/private/AddOrder" and seen["headers"]["API-Key"] == "KEY" and "API-Sign" in seen["headers"]
    assert seen["body"]["ordertype"] == ["stop-loss"] and seen["body"]["pair"] == ["XBTUSD"] and seen["body"]["cl_ord_id"] == ["nsq-x-SL"]
    assert o.id == "OABC-123" and not k.native_brackets


def test_alpaca_bracket_request():
    seen = {}

    def handler(req: httpx.Request):
        if req.method == "GET":
            return httpx.Response(404, json={"message": "not found"})
        seen["path"], seen["headers"], seen["json"] = req.url.path, req.headers, json.loads(req.content)
        return httpx.Response(200, json={"id": "o1", "client_order_id": "nsq-1", "symbol": "AAPL", "side": "buy", "type": "market",
                                         "qty": "10", "status": "accepted", "legs": [
                                             {"id": "l1", "symbol": "AAPL", "side": "sell", "type": "limit", "limit_price": "240", "qty": "10", "status": "held"},
                                             {"id": "l2", "symbol": "AAPL", "side": "sell", "type": "stop", "stop_price": "228", "qty": "10", "status": "held"}]})
    a = AlpacaBroker("ID", "SECRET", client=httpx.Client(transport=httpx.MockTransport(handler)))
    r = a.place_bracket("AAPL", "buy", 10, 228.0, 240.0, "nsq-1")
    j = seen["json"]
    assert seen["path"] == "/v2/orders" and j["order_class"] == "bracket" and j["client_order_id"] == "nsq-1"
    assert j["take_profit"] == {"limit_price": "240.0"} and j["stop_loss"] == {"stop_price": "228.0"}
    assert seen["headers"]["APCA-API-KEY-ID"] == "ID"
    assert r.stop_order.id == "l2" and r.target_order.id == "l1"
    assert a.permissions()["withdrawals"] is False


def test_coming_soon_adapters_refuse():
    import pytest
    from nsq.brokers import BrokerError, build
    for n in ("capital", "ig", "oanda", "mt5", "cmc"):
        with pytest.raises(BrokerError):
            build(n)
