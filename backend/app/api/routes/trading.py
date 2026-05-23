from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_safety_controller, get_trading_engine, require_api_key
from app.db.session import get_session
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
) -> dict:
    result = await engine.process_signal(signal, market)
    return await PaperTradingStore(session).record_submission(result, market)


@router.post("/positions/{symbol}/close")
async def close_position(
    symbol: str,
    side: PositionSide,
    amount: float | None = None,
    exit_price: float | None = None,
    engine: TradingEngine = Depends(get_trading_engine),
    session: AsyncSession = Depends(get_session),
) -> dict:
    result = await engine.close_position(symbol, side, amount)
    if result.get("status") == "paper_closed":
        result.update(await PaperTradingStore(session).close_positions(symbol, side.value, amount, exit_price))
    return result


@router.post("/kill-switch/enable")
async def enable_kill_switch(controller: SafetyController = Depends(get_safety_controller)) -> dict[str, bool]:
    controller.enable_kill_switch()
    return {"kill_switch_enabled": True}


@router.post("/kill-switch/disable")
async def disable_kill_switch(controller: SafetyController = Depends(get_safety_controller)) -> dict[str, bool]:
    controller.disable_kill_switch()
    return {"kill_switch_enabled": False}
