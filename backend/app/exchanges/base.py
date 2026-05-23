from abc import ABC, abstractmethod
from typing import Any

from app.trading.schemas import OrderRequest, Position


class ExchangeClient(ABC):
    """Exchange adapter boundary for futures execution."""

    @abstractmethod
    async def load_markets(self) -> None:
        raise NotImplementedError

    @abstractmethod
    async def set_leverage(self, symbol: str, leverage: int) -> None:
        raise NotImplementedError

    @abstractmethod
    async def ensure_hedge_mode(self) -> None:
        raise NotImplementedError

    @abstractmethod
    async def create_order(self, order: OrderRequest) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    async def close_position(self, symbol: str, position_side: str, amount: float | None = None) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    async def fetch_positions(self) -> list[Position]:
        raise NotImplementedError

    @abstractmethod
    async def fetch_balance(self) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    async def fetch_ohlcv(self, symbol: str, timeframe: str, limit: int = 200) -> list[list[float]]:
        raise NotImplementedError

    @abstractmethod
    async def close(self) -> None:
        raise NotImplementedError
