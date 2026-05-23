import pandas as pd

from app.strategies.base import Strategy
from app.trading.enums import SignalAction
from app.trading.schemas import StrategySignal


class ScalpingModeStrategy(Strategy):
    name = "scalping_mode"
    timeframe = "1m"

    def generate_signal(self, symbol: str, candles: pd.DataFrame) -> StrategySignal:
        self.require_columns(candles)
        if len(candles) < 35:
            return self._hold(symbol, "Not enough candles")

        close = candles["close"]
        ema_9 = close.ewm(span=9, adjust=False).mean()
        ema_21 = close.ewm(span=21, adjust=False).mean()
        volume_ok = float(candles["volume"].iloc[-1]) > float(candles["volume"].rolling(20).mean().iloc[-1])
        current_close = float(close.iloc[-1])

        if volume_ok and ema_9.iloc[-1] > ema_21.iloc[-1] and ema_9.iloc[-2] <= ema_21.iloc[-2]:
            return StrategySignal(
                strategy_name=self.name,
                symbol=symbol,
                action=SignalAction.OPEN_LONG,
                confidence=0.56,
                entry_price=current_close,
                stop_loss=current_close * 0.996,
                take_profit=current_close * 1.006,
                trailing_stop_pct=0.25,
                reason="Fast scalping EMA cross with volume confirmation",
            )
        if volume_ok and ema_9.iloc[-1] < ema_21.iloc[-1] and ema_9.iloc[-2] >= ema_21.iloc[-2]:
            return StrategySignal(
                strategy_name=self.name,
                symbol=symbol,
                action=SignalAction.OPEN_SHORT,
                confidence=0.56,
                entry_price=current_close,
                stop_loss=current_close * 1.004,
                take_profit=current_close * 0.994,
                trailing_stop_pct=0.25,
                reason="Fast scalping bearish EMA cross with volume confirmation",
            )
        return self._hold(symbol, "No scalping setup")

    def _hold(self, symbol: str, reason: str) -> StrategySignal:
        return StrategySignal(strategy_name=self.name, symbol=symbol, action=SignalAction.HOLD, confidence=0, reason=reason)
