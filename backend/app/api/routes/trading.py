from fastapi import APIRouter, Depends

from app.api.deps import get_safety_controller, get_trading_engine
from app.trading.engine import TradingEngine
from app.trading.enums import PositionSide
from app.trading.safety import SafetyController
from app.trading.schemas import MarketSnapshot, StrategySignal

router = APIRouter(prefix="/trading", tags=["trading"])


@router.post("/signals/process")
async def process_signal(
    signal: StrategySignal,
    market: MarketSnapshot,
    engine: TradingEngine = Depends(get_trading_engine),
) -> dict:
    return await engine.process_signal(signal, market)


@router.post("/positions/{symbol}/close")
async def close_position(
    symbol: str,
    side: PositionSide,
    amount: float | None = None,
    engine: TradingEngine = Depends(get_trading_engine),
) -> dict:
    return await engine.close_position(symbol, side, amount)


@router.post("/kill-switch/enable")
async def enable_kill_switch(controller: SafetyController = Depends(get_safety_controller)) -> dict[str, bool]:
    controller.enable_kill_switch()
    return {"kill_switch_enabled": True}


@router.post("/kill-switch/disable")
async def disable_kill_switch(controller: SafetyController = Depends(get_safety_controller)) -> dict[str, bool]:
    controller.disable_kill_switch()
    return {"kill_switch_enabled": False}
