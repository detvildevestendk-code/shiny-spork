from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Strategy(Base, TimestampMixin, UUIDPrimaryKeyMixin):
    __tablename__ = "strategies"

    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    config: Mapped[dict] = mapped_column(JSONB, default=dict)


class Trade(Base, TimestampMixin, UUIDPrimaryKeyMixin):
    __tablename__ = "trades"

    exchange: Mapped[str] = mapped_column(String(30), nullable=False)
    symbol: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    strategy_name: Mapped[str] = mapped_column(String(100), nullable=False)
    side: Mapped[str] = mapped_column(String(10), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    leverage: Mapped[int] = mapped_column(Integer, nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(28, 12), nullable=False)
    entry_price: Mapped[Decimal | None] = mapped_column(Numeric(28, 12))
    exit_price: Mapped[Decimal | None] = mapped_column(Numeric(28, 12))
    stop_loss: Mapped[Decimal | None] = mapped_column(Numeric(28, 12))
    take_profit: Mapped[Decimal | None] = mapped_column(Numeric(28, 12))
    trailing_stop_pct: Mapped[Decimal | None] = mapped_column(Numeric(8, 4))
    realized_pnl: Mapped[Decimal | None] = mapped_column(Numeric(28, 12))
    fees: Mapped[Decimal | None] = mapped_column(Numeric(28, 12))
    opened_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    metadata_json: Mapped[dict] = mapped_column(JSONB, default=dict)

    orders: Mapped[list["Order"]] = relationship(back_populates="trade")


class Order(Base, TimestampMixin, UUIDPrimaryKeyMixin):
    __tablename__ = "orders"

    trade_id: Mapped[str | None] = mapped_column(ForeignKey("trades.id"))
    exchange_order_id: Mapped[str | None] = mapped_column(String(100), index=True)
    symbol: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    side: Mapped[str] = mapped_column(String(10), nullable=False)
    position_side: Mapped[str] = mapped_column(String(10), nullable=False)
    order_type: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(28, 12), nullable=False)
    price: Mapped[Decimal | None] = mapped_column(Numeric(28, 12))
    stop_price: Mapped[Decimal | None] = mapped_column(Numeric(28, 12))
    reduce_only: Mapped[bool] = mapped_column(Boolean, default=False)
    raw_response: Mapped[dict] = mapped_column(JSONB, default=dict)

    trade: Mapped[Trade | None] = relationship(back_populates="orders")


class AiDecision(Base, TimestampMixin, UUIDPrimaryKeyMixin):
    __tablename__ = "ai_decisions"

    symbol: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    strategy_name: Mapped[str] = mapped_column(String(100), nullable=False)
    allowed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    confidence: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)
    reasons: Mapped[str] = mapped_column(Text, nullable=False)
    model: Mapped[str] = mapped_column(String(80), nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, default=dict)


class RiskEvent(Base, TimestampMixin, UUIDPrimaryKeyMixin):
    __tablename__ = "risk_events"

    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    event_type: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_json: Mapped[dict] = mapped_column(JSONB, default=dict)


class BotSetting(Base, TimestampMixin):
    __tablename__ = "bot_settings"

    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[dict] = mapped_column(JSONB, default=dict)


class SignalDecision(Base, TimestampMixin, UUIDPrimaryKeyMixin):
    __tablename__ = "signal_decisions"

    symbol: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    strategy_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(30), nullable=False)
    confidence: Mapped[Decimal] = mapped_column(Numeric(8, 4), nullable=False)
    decision: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    market_price: Mapped[Decimal | None] = mapped_column(Numeric(28, 12))
    metadata_json: Mapped[dict] = mapped_column(JSONB, default=dict)
