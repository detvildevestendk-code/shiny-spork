from dataclasses import dataclass
from typing import Iterable

from app.core.config import Settings
from app.trading.schemas import MarketSnapshot, Position, TradeDecision


@dataclass
class SafetyState:
    kill_switch_enabled: bool = False
    api_failures: int = 0


class SafetyController:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.state = SafetyState()

    def enable_kill_switch(self) -> None:
        self.state.kill_switch_enabled = True

    def disable_kill_switch(self) -> None:
        self.state.kill_switch_enabled = False

    def record_api_failure(self) -> None:
        self.state.api_failures += 1

    def record_api_success(self) -> None:
        self.state.api_failures = 0

    def evaluate(self, market: MarketSnapshot, positions: Iterable[Position]) -> TradeDecision:
        if self.state.kill_switch_enabled:
            return TradeDecision(allowed=False, reason="Emergency kill switch is enabled")
        if self.state.api_failures >= 3:
            return TradeDecision(allowed=False, reason="API failure detection disabled trading")
        if market.volatility_pct >= self.settings.extreme_volatility_threshold_pct:
            return TradeDecision(allowed=False, reason="Extreme volatility auto-disable is active")
        if self._liquidation_risk_detected(positions):
            return TradeDecision(allowed=False, reason="Liquidation prevention is active")
        return TradeDecision(allowed=True, reason="Safety checks passed")

    @staticmethod
    def _liquidation_risk_detected(positions: Iterable[Position]) -> bool:
        for position in positions:
            if not position.liquidation_price or position.mark_price <= 0:
                continue
            distance_pct = abs(position.mark_price - position.liquidation_price) / position.mark_price * 100
            if distance_pct < 5:
                return True
        return False
