from functools import lru_cache

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
