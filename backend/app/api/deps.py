from functools import lru_cache
from secrets import compare_digest

from fastapi import Header, HTTPException, status

from app.ai.client import OpenAiMarketAnalyzer
from app.ai.trade_filter import AiTradeFilter
from app.core.config import Settings, get_settings
from app.exchanges.factory import get_exchange_client
from app.trading.engine import TradingEngine
from app.trading.risk import RiskManager
from app.trading.safety import SafetyController


@lru_cache
def get_safety_controller() -> SafetyController:
    return SafetyController(get_settings())


def get_trading_engine(settings: Settings = get_settings()) -> TradingEngine:
    analyzer = OpenAiMarketAnalyzer(settings)
    return TradingEngine(
        settings=settings,
        exchange=get_exchange_client(settings),
        risk_manager=RiskManager(settings),
        safety_controller=get_safety_controller(),
        ai_filter=AiTradeFilter(analyzer, settings),
    )


def require_api_key(x_api_key: str | None = Header(default=None)) -> None:
    settings = get_settings()
    if not settings.trading_api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="API key authentication is not configured",
        )
    if not x_api_key or not compare_digest(x_api_key, settings.trading_api_key):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")
