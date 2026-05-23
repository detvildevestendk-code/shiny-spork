import pandas as pd

from app.strategies.base import Strategy
from app.trading.enums import SignalAction
from app.trading.schemas import StrategySignal


class TrendFollowingStrategy(Strategy):
    name = "trend_following"
    timeframe = "15m"

    def generate_signal(self, symbol: str, candles: pd.DataFrame) -> StrategySignal:
        self.require_columns(candles)
        if len(candles) < 210:
            return self._hold(symbol, "Not enough candles")

        close = candles["close"]
        ema_50 = close.ewm(span=50, adjust=False).mean()
        ema_200 = close.ewm(span=200, adjust=False).mean()
        current_close = float(close.iloc[-1])
        atr = self._atr(candles).iloc[-1]

        if ema_50.iloc[-1] > ema_200.iloc[-1] and current_close > ema_50.iloc[-1]:
            return StrategySignal(
                strategy_name=self.name,
                symbol=symbol,
                action=SignalAction.OPEN_LONG,
                confidence=0.62,
                entry_price=current_close,
                stop_loss=current_close - float(atr) * 1.5,
                take_profit=current_close + float(atr) * 3,
                trailing_stop_pct=1.0,
                reason="Price trending above 50/200 EMA structure",
            )
        if ema_50.iloc[-1] < ema_200.iloc[-1] and current_close < ema_50.iloc[-1]:
            return StrategySignal(
                strategy_name=self.name,
                symbol=symbol,
                action=SignalAction.OPEN_SHORT,
                confidence=0.62,
                entry_price=current_close,
                stop_loss=current_close + float(atr) * 1.5,
                take_profit=current_close - float(atr) * 3,
                trailing_stop_pct=1.0,
                reason="Price trending below 50/200 EMA structure",
            )
        return self._hold(symbol, "Trend filter neutral")

    @staticmethod
    def _atr(candles: pd.DataFrame, period: int = 14) -> pd.Series:
        high_low = candles["high"] - candles["low"]
        high_close = (candles["high"] - candles["close"].shift()).abs()
        low_close = (candles["low"] - candles["close"].shift()).abs()
        true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        return true_range.rolling(period).mean()

    def _hold(self, symbol: str, reason: str) -> StrategySignal:
        return StrategySignal(strategy_name=self.name, symbol=symbol, action=SignalAction.HOLD, confidence=0, reason=reason)
