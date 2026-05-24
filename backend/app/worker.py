import asyncio
import logging
from datetime import UTC, datetime

import pandas as pd

from app.ai.client import OpenAiMarketAnalyzer
from app.ai.trade_filter import AiTradeFilter
from app.cache.redis import get_redis
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.db.session import AsyncSessionLocal
from app.exchanges.factory import get_exchange_client
from app.notifications.telegram import TelegramNotifier
from app.strategies.registry import build_default_registry
from app.trading.engine import TradingEngine
from app.trading.paper import PaperTradingStore
from app.trading.risk import RiskManager
from app.trading.safety import SafetyController
from app.trading.schemas import MarketSnapshot

logger = logging.getLogger(__name__)


def _candles_frame(raw_candles: list[list[float]]) -> pd.DataFrame:
    return pd.DataFrame(raw_candles, columns=["timestamp", "open", "high", "low", "close", "volume"])


def _market_snapshot(symbol: str, timeframe: str, candles: pd.DataFrame) -> MarketSnapshot:
    close = float(candles["close"].iloc[-1])
    rolling_high = float(candles["high"].tail(24).max())
    rolling_low = float(candles["low"].tail(24).min())
    volatility_pct = ((rolling_high - rolling_low) / close) * 100 if close else 0
    return MarketSnapshot(
        symbol=symbol,
        timeframe=timeframe,
        close=close,
        volume=float(candles["volume"].iloc[-1]),
        volatility_pct=volatility_pct,
        trend_strength=0,
    )


async def _scan_once(notifier: TelegramNotifier | None = None) -> None:
    settings = get_settings()
    registry = build_default_registry()
    exchange = get_exchange_client(settings)
    engine = TradingEngine(
        settings=settings,
        exchange=exchange,
        risk_manager=RiskManager(settings),
        safety_controller=SafetyController(settings),
        ai_filter=AiTradeFilter(OpenAiMarketAnalyzer(settings), settings),
    )

    try:
        for strategy_name in settings.enabled_strategy_names:
            strategy = registry.get(strategy_name)
            for symbol in settings.symbol_list:
                raw = await exchange.fetch_ohlcv(symbol, strategy.timeframe, limit=250)
                candles = _candles_frame(raw)
                signal = strategy.generate_signal(symbol, candles)
                await notifier.strategy_signal(
                    signal.strategy_name,
                    signal.symbol,
                    signal.action.value,
                    signal.confidence,
                    signal.reason,
                )
                market = _market_snapshot(symbol, strategy.timeframe, candles)
                result = await engine.process_signal(signal, market)
                if result.get("status") == "blocked":
                    await notifier.warning(
                        "Worker trade blocked",
                        result.get("reason", "Trade was blocked"),
                        {"symbol": symbol, "strategy": strategy_name, "action": signal.action.value},
                    )
                async with AsyncSessionLocal() as session:
                    await PaperTradingStore(session, notifier).record_submission(result, market)
                logger.info("Processed paper strategy signal", extra={"symbol": symbol, "strategy": strategy_name, "status": result.get("status")})
    finally:
        await exchange.close()


async def main() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)
    redis = get_redis()
    notifier = TelegramNotifier(settings)
    logger.info("Worker started")
    await notifier.startup(f"{settings.app_name} worker", {"scanning": settings.worker_strategy_scanning_enabled})

    try:
        while True:
            try:
                await redis.set("worker:heartbeat", datetime.now(UTC).isoformat(), ex=settings.strategy_scan_interval_seconds * 3)
                if settings.worker_strategy_scanning_enabled:
                    await _scan_once(notifier)
            except Exception as exc:
                logger.exception("Worker loop failed")
                await notifier.worker_crash(exc, {"component": "worker_loop", "scanning": settings.worker_strategy_scanning_enabled})
            await asyncio.sleep(settings.strategy_scan_interval_seconds)
    finally:
        await notifier.shutdown(f"{settings.app_name} worker")
        await redis.aclose()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as exc:
        logger.exception("Worker crashed")
        try:
            asyncio.run(TelegramNotifier(get_settings()).worker_crash(exc, {"component": "worker_process", "fatal": True}))
        finally:
            raise
