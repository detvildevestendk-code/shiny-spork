import pandas as pd

from app.strategies.base import Strategy
from app.trading.enums import SignalAction
from app.trading.schemas import StrategySignal


class RsiDivergenceStrategy(Strategy):
    name = "rsi_divergence"
    timeframe = "15m"

    def generate_signal(self, symbol: str, candles: pd.DataFrame) -> StrategySignal:
        self.require_columns(candles)
        if len(candles) < 20:
            return self._hold(symbol, "Not enough candles")

        delta = candles["close"].diff()
        gain = delta.clip(lower=0).rolling(14).mean()
        loss = (-delta.clip(upper=0)).rolling(14).mean()
        rsi = 100 - (100 / (1 + gain / loss.replace(0, 1e-9)))
        latest_rsi = float(rsi.iloc[-1])
        latest_close = float(candles["close"].iloc[-1])

        if latest_rsi < 30:
            return StrategySignal(
                strategy_name=self.name,
                symbol=symbol,
                action=SignalAction.OPEN_LONG,
                confidence=0.58,
                entry_price=latest_close,
                stop_loss=latest_close * 0.985,
                take_profit=latest_close * 1.025,
                reason="RSI oversold divergence candidate",
            )
        if latest_rsi > 70:
            return StrategySignal(
                strategy_name=self.name,
                symbol=symbol,
                action=SignalAction.OPEN_SHORT,
                confidence=0.58,
                entry_price=latest_close,
                stop_loss=latest_close * 1.015,
                take_profit=latest_close * 0.975,
                reason="RSI overbought divergence candidate",
            )
        return self._hold(symbol, "No RSI divergence candidate")

    def _hold(self, symbol: str, reason: str) -> StrategySignal:
        return StrategySignal(strategy_name=self.name, symbol=symbol, action=SignalAction.HOLD, confidence=0, reason=reason)
