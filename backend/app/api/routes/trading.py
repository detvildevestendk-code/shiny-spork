from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_safety_controller, get_telegram_notifier, get_trading_engine, require_api_key
from app.db.session import get_session
from app.notifications.telegram import TelegramNotifier
from app.trading.engine import TradingEngine
from app.trading.enums import PositionSide
from app.trading.paper import PaperTradingStore
from app.trading.safety import SafetyController
from app.trading.schemas import MarketSnapshot, StrategySignal

router = APIRouter(prefix="/trading", tags=["trading"], dependencies=[Depends(require_api_key)])


@router.post("/signals/process")
async def process_signal(
    signal: StrategySignal,
    market: MarketSnapshot,
    engine: TradingEngine = Depends(get_trading_engine),
    session: AsyncSession = Depends(get_session),
    notifier: TelegramNotifier = Depends(get_telegram_notifier),
) -> dict:
    await notifier.strategy_signal(
        signal.strategy_name,
        signal.symbol,
        signal.action.value,
        signal.confidence,
        signal.reason,
    )
    result = await engine.process_signal(signal, market)
    if result.get("status") == "blocked":
        await notifier.warning(
            "Trade blocked",
            result.get("reason", "Trade was blocked"),
            {"symbol": signal.symbol, "strategy": signal.strategy_name, "action": signal.action.value},
        )
    return await PaperTradingStore(session, notifier).record_submission(result, market)


@router.post("/positions/{symbol}/close")
async def close_position(
    symbol: str,
    side: PositionSide,
    amount: float | None = None,
    exit_price: float | None = None,
    engine: TradingEngine = Depends(get_trading_engine),
    session: AsyncSession = Depends(get_session),
    notifier: TelegramNotifier = Depends(get_telegram_notifier),
) -> dict:
    result = await engine.close_position(symbol, side, amount)
    if result.get("status") == "paper_closed":
        result.update(await PaperTradingStore(session, notifier).close_positions(symbol, side.value, amount, exit_price))
    return result


@router.post("/kill-switch/enable")
async def enable_kill_switch(
    controller: SafetyController = Depends(get_safety_controller),
    notifier: TelegramNotifier = Depends(get_telegram_notifier),
) -> dict[str, bool]:
    controller.enable_kill_switch()
    await notifier.warning("Kill switch enabled", "Emergency kill switch is now enabled")
    return {"kill_switch_enabled": True}


@router.post("/kill-switch/disable")
async def disable_kill_switch(
    controller: SafetyController = Depends(get_safety_controller),
    notifier: TelegramNotifier = Depends(get_telegram_notifier),
) -> dict[str, bool]:
    controller.disable_kill_switch()
    await notifier.warning("Kill switch disabled", "Emergency kill switch is now disabled")
    return {"kill_switch_enabled": False}
