import logging
from typing import Any

import ccxt.async_support as ccxt

from app.core.config import Settings
from app.exchanges.base import ExchangeClient
from app.trading.enums import OrderSide, OrderType, PositionSide
from app.trading.schemas import OrderRequest, Position

logger = logging.getLogger(__name__)


class CcxtFuturesClient(ExchangeClient):
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.exchange = self._build_exchange(settings)

    def _build_exchange(self, settings: Settings) -> ccxt.Exchange:
        credentials = {
            "bybit": (settings.bybit_api_key, settings.bybit_api_secret),
            "binance": (settings.binance_api_key, settings.binance_api_secret),
        }
        api_key, api_secret = credentials[settings.exchange_name]
        exchange_cls = getattr(ccxt, settings.exchange_name)
        exchange = exchange_cls(
            {
                "apiKey": api_key,
                "secret": api_secret,
                "enableRateLimit": True,
                "options": self._exchange_options(settings.exchange_name),
            }
        )
        if settings.exchange_sandbox and hasattr(exchange, "set_sandbox_mode"):
            exchange.set_sandbox_mode(True)
        return exchange

    @staticmethod
    def _exchange_options(exchange_name: str) -> dict[str, Any]:
        if exchange_name == "binance":
            return {"defaultType": "future", "adjustForTimeDifference": True}
        return {"defaultType": "swap"}

    async def load_markets(self) -> None:
        await self.exchange.load_markets()

    async def set_leverage(self, symbol: str, leverage: int) -> None:
        await self.exchange.set_leverage(leverage, symbol)

    async def ensure_hedge_mode(self) -> None:
        if not self.settings.hedge_mode_enabled:
            return
        try:
            if self.settings.exchange_name == "binance":
                await self.exchange.set_position_mode(True)
            elif self.settings.exchange_name == "bybit":
                await self.exchange.set_position_mode(True)
        except Exception as exc:  # pragma: no cover - exchange-specific behavior
            logger.warning("Unable to set hedge mode automatically: %s", exc)

    async def create_order(self, order: OrderRequest) -> dict[str, Any]:
        params = self._order_params(order)
        if order.leverage:
            await self.set_leverage(order.symbol, order.leverage)
        return await self.exchange.create_order(
            symbol=order.symbol,
            type=order.order_type.value,
            side=order.side.value,
            amount=order.amount,
            price=order.price,
            params=params,
        )

    async def close_position(self, symbol: str, position_side: str, amount: float | None = None) -> dict[str, Any]:
        side = OrderSide.SELL if position_side == PositionSide.LONG else OrderSide.BUY
        params = {"reduceOnly": True, "positionSide": position_side.upper()}
        return await self.exchange.create_order(symbol, OrderType.MARKET.value, side.value, amount, None, params)

    async def fetch_positions(self) -> list[Position]:
        raw_positions = await self.exchange.fetch_positions()
        positions: list[Position] = []
        for item in raw_positions:
            contracts = float(item.get("contracts") or item.get("contractSize") or 0)
            if contracts == 0:
                continue
            side = PositionSide.LONG if (item.get("side") or "").lower() == "long" else PositionSide.SHORT
            positions.append(
                Position(
                    symbol=item["symbol"],
                    side=side,
                    amount=abs(contracts),
                    entry_price=float(item.get("entryPrice") or 0),
                    mark_price=float(item.get("markPrice") or item.get("lastPrice") or 0),
                    unrealized_pnl=float(item.get("unrealizedPnl") or 0),
                    liquidation_price=(
                        float(item["liquidationPrice"])
                        if item.get("liquidationPrice") is not None
                        else None
                    ),
                    leverage=int(float(item.get("leverage") or self.settings.default_leverage)),
                )
            )
        return positions

    async def fetch_balance(self) -> dict[str, Any]:
        return await self.exchange.fetch_balance()

    async def fetch_ohlcv(self, symbol: str, timeframe: str, limit: int = 200) -> list[list[float]]:
        return await self.exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)

    async def close(self) -> None:
        await self.exchange.close()

    def _order_params(self, order: OrderRequest) -> dict[str, Any]:
        params: dict[str, Any] = {"reduceOnly": order.reduce_only}
        if self.settings.hedge_mode_enabled:
            params["positionSide"] = order.position_side.upper()
        if order.client_order_id:
            params["clientOrderId"] = order.client_order_id
        if order.order_type == OrderType.STOP and order.stop_price:
            params["stopPrice"] = order.stop_price
        return params
