from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, PositiveFloat, PositiveInt

from app.trading.enums import OrderSide, OrderType, PositionSide, SignalAction, TradeStatus


class MarketSnapshot(BaseModel):
    symbol: str
    timeframe: str
    close: float
    volume: float
    volatility_pct: float
    trend_strength: float = 0
    metadata: dict[str, Any] = Field(default_factory=dict)


class StrategySignal(BaseModel):
    strategy_name: str
    symbol: str
    action: SignalAction
    confidence: float = Field(ge=0, le=1)
    entry_price: float | None = None
    stop_loss: float | None = None
    take_profit: float | None = None
    trailing_stop_pct: float | None = None
    leverage: PositiveInt | None = None
    reason: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class OrderRequest(BaseModel):
    symbol: str
    side: OrderSide
    position_side: PositionSide
    order_type: OrderType = OrderType.MARKET
    amount: PositiveFloat
    price: PositiveFloat | None = None
    stop_price: PositiveFloat | None = None
    reduce_only: bool = False
    leverage: PositiveInt | None = None
    client_order_id: str | None = None


class TradeIntent(BaseModel):
    signal: StrategySignal
    order: OrderRequest
    account_equity: PositiveFloat
    risk_amount: PositiveFloat


class TradeDecision(BaseModel):
    allowed: bool
    reason: str
    ai_confidence: float | None = None
    risk_metadata: dict[str, Any] = Field(default_factory=dict)


class Position(BaseModel):
    symbol: str
    side: PositionSide
    amount: float
    entry_price: float
    mark_price: float
    unrealized_pnl: float
    liquidation_price: float | None = None
    leverage: int
    opened_at: datetime | None = None


class TradeRecord(BaseModel):
    id: UUID
    symbol: str
    side: PositionSide
    status: TradeStatus
    entry_price: float | None = None
    exit_price: float | None = None
    realized_pnl: float | None = None
    opened_at: datetime | None = None
    closed_at: datetime | None = None
