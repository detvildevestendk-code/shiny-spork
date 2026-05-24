from decimal import Decimal
from typing import Any

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import SignalDecision
from app.trading.schemas import MarketSnapshot, StrategySignal


async def record_signal_decision(
    session: AsyncSession,
    signal: StrategySignal,
    market: MarketSnapshot,
    decision: str,
    reason: str,
    metadata: dict[str, Any] | None = None,
) -> SignalDecision:
    row = SignalDecision(
        symbol=signal.symbol,
        strategy_name=signal.strategy_name,
        action=signal.action.value,
        confidence=Decimal(str(signal.confidence)),
        decision=decision,
        reason=reason,
        market_price=Decimal(str(market.close)),
        metadata_json=metadata or {},
    )
    session.add(row)
    await session.commit()
    return row


async def latest_signal_decision(session: AsyncSession) -> SignalDecision | None:
    return await session.scalar(select(SignalDecision).order_by(desc(SignalDecision.created_at)).limit(1))
