import pandas as pd

from app.strategies.base import Strategy
from app.trading.enums import SignalAction
from app.trading.schemas import StrategySignal


class EmaCrossoverStrategy(Strategy):
    name = "ema_crossover"
    timeframe = "5m"

    def __init__(
        self,
        fast_period: int = 12,
        slow_period: int = 26,
        stop_loss_pct: float = 1.2,
        take_profit_pct: float = 2.4,
    ) -> None:
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.stop_loss_pct = stop_loss_pct
        self.take_profit_pct = take_profit_pct

    def generate_signal(self, symbol: str, candles: pd.DataFrame) -> StrategySignal:
        self.require_columns(candles)
        if len(candles) < self.slow_period + 2:
            return self._hold(symbol, "Not enough candles")

        frame = candles.copy()
        frame["ema_fast"] = frame["close"].ewm(span=self.fast_period, adjust=False).mean()
        frame["ema_slow"] = frame["close"].ewm(span=self.slow_period, adjust=False).mean()

        previous = frame.iloc[-2]
        current = frame.iloc[-1]
        close = float(current["close"])

        crossed_up = previous["ema_fast"] <= previous["ema_slow"] and current["ema_fast"] > current["ema_slow"]
        crossed_down = previous["ema_fast"] >= previous["ema_slow"] and current["ema_fast"] < current["ema_slow"]

        if crossed_up:
            return StrategySignal(
                strategy_name=self.name,
                symbol=symbol,
                action=SignalAction.OPEN_LONG,
                confidence=0.68,
                entry_price=close,
                stop_loss=close * (1 - self.stop_loss_pct / 100),
                take_profit=close * (1 + self.take_profit_pct / 100),
                trailing_stop_pct=0.8,
                reason="Fast EMA crossed above slow EMA",
            )
        if crossed_down:
            return StrategySignal(
                strategy_name=self.name,
                symbol=symbol,
                action=SignalAction.OPEN_SHORT,
                confidence=0.68,
                entry_price=close,
                stop_loss=close * (1 + self.stop_loss_pct / 100),
                take_profit=close * (1 - self.take_profit_pct / 100),
                trailing_stop_pct=0.8,
                reason="Fast EMA crossed below slow EMA",
            )
        return self._hold(symbol, "No EMA crossover")

    def _hold(self, symbol: str, reason: str) -> StrategySignal:
        return StrategySignal(
            strategy_name=self.name,
            symbol=symbol,
            action=SignalAction.HOLD,
            confidence=0,
            reason=reason,
        )
