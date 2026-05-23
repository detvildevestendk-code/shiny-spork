from datetime import UTC, datetime
from typing import Any

from app.ai.trade_filter import AiTradeFilter
from app.core.config import Settings
from app.exchanges.base import ExchangeClient
from app.trading.enums import OrderSide, OrderType, PositionSide, SignalAction
from app.trading.risk import RiskManager
from app.trading.safety import SafetyController
from app.trading.schemas import MarketSnapshot, OrderRequest, StrategySignal, TradeDecision


class TradingEngine:
    def __init__(
        self,
        settings: Settings,
        exchange: ExchangeClient,
        risk_manager: RiskManager,
        safety_controller: SafetyController,
        ai_filter: AiTradeFilter,
    ) -> None:
        self.settings = settings
        self.exchange = exchange
        self.risk_manager = risk_manager
        self.safety_controller = safety_controller
        self.ai_filter = ai_filter

    async def process_signal(
        self,
        signal: StrategySignal,
        market: MarketSnapshot,
        daily_realized_pnl: float = 0,
        losing_streak: int = 0,
        last_loss_at: datetime | None = None,
        recent_news: list[str] | None = None,
    ) -> dict[str, Any]:
        paper_mode = self.settings.paper_trading_enabled or not self.settings.live_trading_enabled
        if paper_mode:
            positions = []
            account_equity = float(self.settings.paper_trading_equity)
        else:
            positions = await self.exchange.fetch_positions()
            balance = await self.exchange.fetch_balance()
            account_equity = self._account_equity(balance)

        for decision in (
            self.safety_controller.evaluate(market, positions),
            self.risk_manager.evaluate(
                signal,
                positions,
                daily_realized_pnl=daily_realized_pnl,
                account_equity=account_equity,
                losing_streak=losing_streak,
                last_loss_at=last_loss_at,
            ),
        ):
            if not decision.allowed:
                return self._blocked(signal, decision)

        ai_decision = await self.ai_filter.evaluate(signal, market, recent_news)
        if not ai_decision.allowed:
            return self._blocked(signal, ai_decision)

        order = self._build_order(signal, account_equity)
        if paper_mode:
            return {
                "status": "paper_submitted",
                "signal": signal.model_dump(),
                "order": order.model_dump(),
                "ai_confidence": ai_decision.ai_confidence,
                "exchange_response": None,
                "live_trading_enabled": False,
                "submitted_at": datetime.now(UTC).isoformat(),
            }

        exchange_response = await self.exchange.create_order(order)
        return {
            "status": "submitted",
            "signal": signal.model_dump(),
            "order": order.model_dump(),
            "ai_confidence": ai_decision.ai_confidence,
            "exchange_response": exchange_response,
            "submitted_at": datetime.now(UTC).isoformat(),
        }

    async def close_position(self, symbol: str, side: PositionSide, amount: float | None = None) -> dict[str, Any]:
        if not self.settings.live_trading_enabled:
            return {"status": "paper_closed", "symbol": symbol, "side": side.value, "amount": amount}
        return await self.exchange.close_position(symbol, side.value, amount)

    def _build_order(self, signal: StrategySignal, account_equity: float) -> OrderRequest:
        if not signal.entry_price or not signal.stop_loss:
            raise ValueError("Opening signals require entry_price and stop_loss")
        amount, _risk_amount = self.risk_manager.position_size(account_equity, signal.entry_price, signal.stop_loss)
        leverage = min(signal.leverage or self.settings.default_leverage, self.settings.max_leverage)
        if signal.action == SignalAction.OPEN_LONG:
            side = OrderSide.BUY
            position_side = PositionSide.LONG
        elif signal.action == SignalAction.OPEN_SHORT:
            side = OrderSide.SELL
            position_side = PositionSide.SHORT
        else:
            raise ValueError(f"Unsupported execution signal: {signal.action}")
        return OrderRequest(
            symbol=signal.symbol,
            side=side,
            position_side=position_side,
            order_type=OrderType.MARKET,
            amount=amount,
            leverage=leverage,
        )

    @staticmethod
    def _account_equity(balance: dict[str, Any]) -> float:
        total = balance.get("total") or {}
        free = balance.get("free") or {}
        return float(total.get("USDT") or free.get("USDT") or balance.get("USDT", {}).get("total") or 0)

    @staticmethod
    def _blocked(signal: StrategySignal, decision: TradeDecision) -> dict[str, Any]:
        return {
            "status": "blocked",
            "signal": signal.model_dump(),
            "reason": decision.reason,
            "ai_confidence": decision.ai_confidence,
            "risk_metadata": decision.risk_metadata,
        }
