import pandas as pd

from app.strategies.base import Strategy
from app.trading.enums import SignalAction
from app.trading.schemas import StrategySignal


class RsiMomentumStrategy(Strategy):
    name = "rsi_momentum"
    timeframe = "5m"

    def generate_signal(self, symbol: str, candles: pd.DataFrame) -> StrategySignal:
        self.require_columns(candles)
        if len(candles) < 35:
            return self._hold(symbol, "Not enough candles for RSI momentum")

        close = candles["close"]
        delta = close.diff()
        gain = delta.clip(lower=0).rolling(14).mean()
        loss = (-delta.clip(upper=0)).rolling(14).mean().replace(0, 1e-9)
        rsi = 100 - (100 / (1 + gain / loss))
        current_rsi = float(rsi.iloc[-1])
        previous_rsi = float(rsi.iloc[-2])
        current_close = float(close.iloc[-1])
        ema_21 = close.ewm(span=21, adjust=False).mean()

        if current_rsi > 58 and current_rsi > previous_rsi and current_close > float(ema_21.iloc[-1]):
            return StrategySignal(
                strategy_name=self.name,
                symbol=symbol,
                action=SignalAction.OPEN_LONG,
                confidence=min(0.92, 0.56 + (current_rsi - 58) / 100),
                entry_price=current_close,
                stop_loss=current_close * 0.988,
                take_profit=current_close * 1.024,
                trailing_stop_pct=0.8,
                reason=f"RSI momentum bullish: RSI {current_rsi:.1f} rising above EMA trend",
            )
        if current_rsi < 42 and current_rsi < previous_rsi and current_close < float(ema_21.iloc[-1]):
            return StrategySignal(
                strategy_name=self.name,
                symbol=symbol,
                action=SignalAction.OPEN_SHORT,
                confidence=min(0.92, 0.56 + (42 - current_rsi) / 100),
                entry_price=current_close,
                stop_loss=current_close * 1.012,
                take_profit=current_close * 0.976,
                trailing_stop_pct=0.8,
                reason=f"RSI momentum bearish: RSI {current_rsi:.1f} falling below EMA trend",
            )
        return self._hold(symbol, f"RSI momentum neutral: RSI {current_rsi:.1f}")

    def _hold(self, symbol: str, reason: str) -> StrategySignal:
        return StrategySignal(strategy_name=self.name, symbol=symbol, action=SignalAction.HOLD, confidence=0, reason=reason)
