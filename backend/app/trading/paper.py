from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.models import Order, Trade
from app.trading.enums import TradeStatus
from app.trading.schemas import MarketSnapshot


def _decimal(value: Any) -> Decimal | None:
    if value is None:
        return None
    return Decimal(str(value))


class PaperTradingStore:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.paper_equity = Decimal(str(get_settings().paper_trading_equity))

    async def record_submission(self, result: dict[str, Any], market: MarketSnapshot) -> dict[str, Any]:
        if result.get("status") != "paper_submitted":
            return result

        signal = result["signal"]
        order = result["order"]
        now = datetime.now(UTC)
        trade = Trade(
            exchange="paper",
            symbol=signal["symbol"],
            strategy_name=signal["strategy_name"],
            side=order["position_side"],
            status=TradeStatus.OPEN.value,
            leverage=order.get("leverage") or 1,
            amount=_decimal(order["amount"]),
            entry_price=_decimal(signal.get("entry_price")),
            stop_loss=_decimal(signal.get("stop_loss")),
            take_profit=_decimal(signal.get("take_profit")),
            trailing_stop_pct=_decimal(signal.get("trailing_stop_pct")),
            opened_at=now,
            metadata_json={
                "paper": True,
                "signal": signal,
                "market": market.model_dump(),
                "ai_confidence": result.get("ai_confidence"),
                "paper_equity": float(self.paper_equity),
            },
        )
        order_row = Order(
            trade=trade,
            exchange_order_id=None,
            symbol=order["symbol"],
            side=order["side"],
            position_side=order["position_side"],
            order_type=order["order_type"],
            status="paper_submitted",
            amount=_decimal(order["amount"]),
            price=_decimal(order.get("price")),
            stop_price=_decimal(order.get("stop_price")),
            reduce_only=bool(order.get("reduce_only")),
            raw_response={"paper": True, "order": order},
        )
        self.session.add_all([trade, order_row])
        await self.session.commit()
        result["paper_trade_id"] = trade.id
        return result

    async def close_positions(
        self,
        symbol: str,
        side: str,
        amount: float | None = None,
        exit_price: float | None = None,
    ) -> dict[str, Any]:
        query = (
            select(Trade)
            .where(Trade.exchange == "paper")
            .where(Trade.symbol == symbol)
            .where(Trade.side == side)
            .where(Trade.status == TradeStatus.OPEN.value)
            .order_by(Trade.opened_at.asc())
        )
        trades = list((await self.session.scalars(query)).all())
        remaining = Decimal(str(amount)) if amount is not None else None
        closed = 0
        realized = Decimal("0")
        now = datetime.now(UTC)

        for trade in trades:
            if remaining is not None and remaining <= 0:
                break
            close_amount = trade.amount if remaining is None else min(trade.amount, remaining)
            effective_exit = _decimal(exit_price) or trade.entry_price or Decimal("0")
            entry = trade.entry_price or effective_exit
            pnl = (effective_exit - entry) * close_amount
            if trade.side == "short":
                pnl = -pnl

            trade.status = TradeStatus.CLOSED.value
            trade.exit_price = effective_exit
            trade.realized_pnl = pnl
            trade.closed_at = now
            trade.metadata_json = {**(trade.metadata_json or {}), "paper_close_amount": str(close_amount)}
            realized += pnl
            closed += 1
            if remaining is not None:
                remaining -= close_amount

        await self.session.commit()
        return {"paper_positions_closed": closed, "paper_realized_pnl": float(realized)}

    async def dashboard_summary(self) -> dict[str, Any]:
        open_trades = list(
            (
                await self.session.scalars(
                    select(Trade)
                    .where(Trade.exchange == "paper")
                    .where(Trade.status == TradeStatus.OPEN.value)
                    .order_by(desc(Trade.opened_at))
                )
            ).all()
        )
        closed_trades = list(
            (
                await self.session.scalars(
                    select(Trade)
                    .where(Trade.exchange == "paper")
                    .where(Trade.status == TradeStatus.CLOSED.value)
                    .order_by(desc(Trade.closed_at))
                    .limit(200)
                )
            ).all()
        )
        realized = sum((trade.realized_pnl or Decimal("0")) for trade in closed_trades)
        positions = [self._position_payload(trade) for trade in open_trades]
        exposure = sum(item["notional"] for item in positions)
        equity = self._paper_equity(open_trades)
        return {
            "mode": "paper",
            "live_pnl": float(realized),
            "open_positions": positions,
            "risk_exposure_pct": float((Decimal(str(exposure)) / equity) * 100) if equity > 0 else 0,
            "ai_confidence_score": self._latest_ai_confidence(open_trades),
            "exchange_connection_status": "paper",
            "strategy_toggles": {
                "ema_crossover": True,
                "rsi_divergence": True,
                "volume_breakout": True,
                "trend_following": True,
                "mean_reversion": True,
                "scalping_mode": True,
            },
            "telegram_alerts_enabled": False,
        }

    async def trade_history(self, limit: int = 100) -> dict[str, Any]:
        trades = list(
            (
                await self.session.scalars(
                    select(Trade)
                    .where(Trade.exchange == "paper")
                    .order_by(desc(Trade.created_at))
                    .limit(limit)
                )
            ).all()
        )
        return {"items": [self._trade_payload(trade) for trade in trades], "total": len(trades)}

    def _paper_equity(self, trades: list[Trade]) -> Decimal:
        for trade in trades:
            equity = (trade.metadata_json or {}).get("paper_equity")
            if equity is not None:
                return Decimal(str(equity))
        return self.paper_equity

    @staticmethod
    def _latest_ai_confidence(trades: list[Trade]) -> float | None:
        for trade in trades:
            confidence = (trade.metadata_json or {}).get("ai_confidence")
            if confidence is not None:
                return float(confidence)
        return None

    @staticmethod
    def _position_payload(trade: Trade) -> dict[str, Any]:
        metadata = trade.metadata_json or {}
        market = metadata.get("market") or {}
        mark_price = Decimal(str(market.get("close") or trade.entry_price or 0))
        amount = trade.amount or Decimal("0")
        notional = amount * mark_price
        entry = trade.entry_price or mark_price
        unrealized = (mark_price - entry) * amount
        if trade.side == "short":
            unrealized = -unrealized
        return {
            "id": trade.id,
            "symbol": trade.symbol,
            "side": trade.side,
            "amount": float(amount),
            "entry_price": float(entry),
            "mark_price": float(mark_price),
            "notional": float(notional),
            "unrealized_pnl": float(unrealized),
            "leverage": trade.leverage,
            "opened_at": trade.opened_at.isoformat() if trade.opened_at else None,
        }

    @staticmethod
    def _trade_payload(trade: Trade) -> dict[str, Any]:
        return {
            "id": trade.id,
            "symbol": trade.symbol,
            "strategy_name": trade.strategy_name,
            "side": trade.side,
            "status": trade.status,
            "amount": float(trade.amount or 0),
            "entry_price": float(trade.entry_price or 0),
            "exit_price": float(trade.exit_price or 0) if trade.exit_price is not None else None,
            "realized_pnl": float(trade.realized_pnl or 0) if trade.realized_pnl is not None else None,
            "opened_at": trade.opened_at.isoformat() if trade.opened_at else None,
            "closed_at": trade.closed_at.isoformat() if trade.closed_at else None,
        }
