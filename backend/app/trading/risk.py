from datetime import UTC, datetime, timedelta
from typing import Iterable

from app.core.config import Settings
from app.trading.enums import SignalAction
from app.trading.schemas import Position, StrategySignal, TradeDecision


class RiskManager:
    """Enforces hard risk rules before AI or execution can approve a trade."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def evaluate(
        self,
        signal: StrategySignal,
        positions: Iterable[Position],
        daily_realized_pnl: float,
        account_equity: float,
        losing_streak: int,
        last_loss_at: datetime | None,
    ) -> TradeDecision:
        if signal.action == SignalAction.HOLD:
            return TradeDecision(allowed=False, reason="Strategy requested hold")

        max_daily_loss = account_equity * (self.settings.max_daily_loss_pct / 100)
        if daily_realized_pnl <= -max_daily_loss:
            return TradeDecision(allowed=False, reason="Max daily loss protection is active")

        open_positions = list(positions)
        if self._is_opening_signal(signal) and len(open_positions) >= self.settings.max_open_trades:
            return TradeDecision(allowed=False, reason="Max open trades limit reached")

        leverage = signal.leverage or self.settings.default_leverage
        if leverage > self.settings.max_leverage:
            return TradeDecision(allowed=False, reason="Requested leverage exceeds configured maximum")

        if self._in_losing_streak_cooldown(losing_streak, last_loss_at):
            return TradeDecision(allowed=False, reason="Cooldown active after losing streak")

        exposure_pct = self._exposure_pct(open_positions, account_equity)
        if exposure_pct >= self.settings.max_account_exposure_pct:
            return TradeDecision(allowed=False, reason="Account exposure limit reached")

        return TradeDecision(
            allowed=True,
            reason="Risk checks passed",
            risk_metadata={"exposure_pct": exposure_pct, "leverage": leverage},
        )

    def position_size(self, account_equity: float, entry_price: float, stop_loss: float) -> tuple[float, float]:
        risk_amount = account_equity * (self.settings.max_position_risk_pct / 100)
        stop_distance = abs(entry_price - stop_loss)
        if stop_distance <= 0:
            raise ValueError("stop_loss must be different from entry_price")
        amount = risk_amount / stop_distance
        return amount, risk_amount

    def _in_losing_streak_cooldown(self, losing_streak: int, last_loss_at: datetime | None) -> bool:
        if losing_streak < 3 or last_loss_at is None:
            return False
        cooldown_until = last_loss_at + timedelta(minutes=self.settings.losing_streak_cooldown_minutes)
        return datetime.now(UTC) < cooldown_until

    @staticmethod
    def _is_opening_signal(signal: StrategySignal) -> bool:
        return signal.action in {SignalAction.OPEN_LONG, SignalAction.OPEN_SHORT}

    @staticmethod
    def _exposure_pct(positions: Iterable[Position], account_equity: float) -> float:
        if account_equity <= 0:
            return 100
        notional = sum(abs(position.amount * position.mark_price) for position in positions)
        return (notional / account_equity) * 100
