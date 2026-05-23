from app.core.config import Settings, get_settings
from app.exchanges.base import ExchangeClient
from app.exchanges.ccxt_client import CcxtFuturesClient


def get_exchange_client(settings: Settings | None = None) -> ExchangeClient:
    return CcxtFuturesClient(settings or get_settings())
