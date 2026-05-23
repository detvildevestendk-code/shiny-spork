import pandas as pd

from app.strategies.base import Strategy
from app.trading.enums import SignalAction
from app.trading.schemas import StrategySignal


class MeanReversionStrategy(Strategy):
    name = "mean_reversion"
    timeframe = "15m"

    def generate_signal(self, symbol: str, candles: pd.DataFrame) -> StrategySignal:
        self.require_columns(candles)
        if len(candles) < 30:
            return self._hold(symbol, "Not enough candles")

        close = candles["close"]
        mean = close.rolling(20).mean()
        std = close.rolling(20).std()
        upper = mean + std * 2
        lower = mean - std * 2
        current_close = float(close.iloc[-1])
        current_mean = float(mean.iloc[-1])

        if current_close < float(lower.iloc[-1]):
            return StrategySignal(
                strategy_name=self.name,
                symbol=symbol,
                action=SignalAction.OPEN_LONG,
                confidence=0.6,
                entry_price=current_close,
                stop_loss=current_close * 0.985,
                take_profit=current_mean,
                reason="Price extended below lower band",
            )
        if current_close > float(upper.iloc[-1]):
            return StrategySignal(
                strategy_name=self.name,
                symbol=symbol,
                action=SignalAction.OPEN_SHORT,
                confidence=0.6,
                entry_price=current_close,
                stop_loss=current_close * 1.015,
                take_profit=current_mean,
                reason="Price extended above upper band",
            )
        return self._hold(symbol, "Price near mean")

    def _hold(self, symbol: str, reason: str) -> StrategySignal:
        return StrategySignal(strategy_name=self.name, symbol=symbol, action=SignalAction.HOLD, confidence=0, reason=reason)
