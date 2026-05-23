import pandas as pd

from app.strategies.base import Strategy
from app.trading.enums import SignalAction
from app.trading.schemas import StrategySignal


class VolumeBreakoutStrategy(Strategy):
    name = "volume_breakout"
    timeframe = "5m"

    def generate_signal(self, symbol: str, candles: pd.DataFrame) -> StrategySignal:
        self.require_columns(candles)
        if len(candles) < 25:
            return self._hold(symbol, "Not enough candles")

        current = candles.iloc[-1]
        previous_high = float(candles["high"].iloc[-21:-1].max())
        previous_low = float(candles["low"].iloc[-21:-1].min())
        avg_volume = float(candles["volume"].iloc[-21:-1].mean())
        close = float(current["close"])
        volume_spike = float(current["volume"]) > avg_volume * 1.8

        if volume_spike and close > previous_high:
            return StrategySignal(
                strategy_name=self.name,
                symbol=symbol,
                action=SignalAction.OPEN_LONG,
                confidence=0.64,
                entry_price=close,
                stop_loss=previous_high * 0.992,
                take_profit=close * 1.02,
                trailing_stop_pct=0.7,
                reason="Volume breakout above recent resistance",
            )
        if volume_spike and close < previous_low:
            return StrategySignal(
                strategy_name=self.name,
                symbol=symbol,
                action=SignalAction.OPEN_SHORT,
                confidence=0.64,
                entry_price=close,
                stop_loss=previous_low * 1.008,
                take_profit=close * 0.98,
                trailing_stop_pct=0.7,
                reason="Volume breakdown below recent support",
            )
        return self._hold(symbol, "No volume breakout")

    def _hold(self, symbol: str, reason: str) -> StrategySignal:
        return StrategySignal(strategy_name=self.name, symbol=symbol, action=SignalAction.HOLD, confidence=0, reason=reason)
