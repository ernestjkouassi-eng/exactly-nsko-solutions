"""Broker registry.

Real adapters: paper (default), alpaca, kraken, coinbase (official SDK, optional), ibkr (ib_async, optional).
Coming soon (could not be verified against official docs from the build machine): capital.com, IG, OANDA, MT5.
Not supported: CMC Markets (no bot / trading API for retail).
"""
from __future__ import annotations

import threading

from .base import BrokerAdapter, BrokerError, ComingSoon

_BLOCKED = ("its official API docs host was blocked on the build machine, so the endpoints could not be checked. "
            "The engine never ships endpoints it has not verified.")


class CapitalComBroker(ComingSoon):
    name, title = "capital", "Capital.com"
    status_reason = "open-api.capital.com: " + _BLOCKED
    docs_url = "https://open-api.capital.com/"
    withdraw_page = "https://capital.com/trading/platform/"


class IGBroker(ComingSoon):
    name, title = "ig", "IG"
    status_reason = "labs.ig.com: " + _BLOCKED
    docs_url = "https://labs.ig.com/rest-trading-api-reference"
    withdraw_page = "https://www.ig.com/uk/myig/"


class OandaBroker(ComingSoon):
    name, title = "oanda", "OANDA"
    status_reason = "developer.oanda.com: " + _BLOCKED
    docs_url = "https://developer.oanda.com/rest-live-v20/introduction/"
    withdraw_page = "https://www.oanda.com/account/login"


class MT5Broker(ComingSoon):
    name, title = "mt5", "MetaTrader 5"
    status_reason = ("the MetaTrader5 Python package is Windows-only and has no Linux wheel, so it could not be installed "
                     "or checked on the build machine. It also needs the MT5 terminal running on Windows.")
    docs_url = "https://www.mql5.com/en/docs/python_metatrader5"


class CMCBroker(ComingSoon):
    name, title = "cmc", "CMC Markets"
    status = "unsupported"
    status_reason = "CMC Markets does not offer a bot / trading API for retail accounts. Not supported."


def catalogue() -> list[dict]:
    from .alpaca import AlpacaBroker
    from .coinbase import CoinbaseBroker
    from .ibkr import IBKRBroker
    from .kraken import KrakenBroker
    from .paper import PaperBroker
    out = []
    for cls in (PaperBroker, AlpacaBroker, KrakenBroker, CoinbaseBroker, IBKRBroker, CapitalComBroker, IGBroker,
                OandaBroker, MT5Broker, CMCBroker):
        out.append({"name": cls.name, "title": cls.title, "status": cls.status, "reason": cls.status_reason,
                    "native_brackets": cls.native_brackets, "markets": list(cls.markets), "docs": cls.docs_url,
                    "withdraw_page": cls.withdraw_page})
    return out


_active: BrokerAdapter | None = None
_lock = threading.Lock()


def active() -> BrokerAdapter:
    """The broker the engine trades with. Paper unless the user connected a real one."""
    global _active
    with _lock:
        if _active is None:
            from .paper import PaperBroker
            _active = PaperBroker()
        return _active


def set_active(b: BrokerAdapter | None) -> None:
    global _active
    with _lock:
        _active = b


def build(name: str, live: bool = False) -> BrokerAdapter:
    """Create an adapter with keys from the vault. Keys never leave the vault except into the adapter."""
    from .. import vault
    if name == "paper":
        from .paper import PaperBroker
        return PaperBroker()
    if name == "alpaca":
        from .alpaca import AlpacaBroker
        return AlpacaBroker(vault.get("alpaca.key_id") or "", vault.get("alpaca.secret") or "", live=live)
    if name == "kraken":
        from .kraken import KrakenBroker
        return KrakenBroker(vault.get("kraken.key") or "", vault.get("kraken.secret") or "")
    if name == "coinbase":
        from .coinbase import CoinbaseBroker
        return CoinbaseBroker(vault.get("coinbase.key") or "", vault.get("coinbase.secret") or "")
    if name == "ibkr":
        from .ibkr import IBKRBroker
        return IBKRBroker()
    for cls in (CapitalComBroker, IGBroker, OandaBroker, MT5Broker, CMCBroker):
        if cls.name == name:
            raise BrokerError(f"{cls.title}: {cls.status_reason}")
    raise BrokerError(f"unknown broker {name}")


__all__ = ["BrokerAdapter", "BrokerError", "active", "set_active", "build", "catalogue"]
