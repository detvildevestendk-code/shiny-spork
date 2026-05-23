from abc import ABC, abstractmethod

import pandas as pd

from app.trading.schemas import StrategySignal


class Strategy(ABC):
    name: str
    timeframe: str = "5m"

    @abstractmethod
    def generate_signal(self, symbol: str, candles: pd.DataFrame) -> StrategySignal:
        raise NotImplementedError

    @staticmethod
    def require_columns(candles: pd.DataFrame) -> None:
        required = {"timestamp", "open", "high", "low", "close", "volume"}
        missing = required.difference(candles.columns)
        if missing:
            raise ValueError(f"Missing required candle columns: {sorted(missing)}")
