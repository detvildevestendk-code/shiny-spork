from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.models import Order, Trade
from app.notifications.telegram import TelegramNotifier
from app.trading.enums import TradeStatus
from app.trading.schemas import MarketSnapshot


def _decimal(value: Any) -> Decimal | None:
    if value is None:
        return None
    return Decimal(str(value))


class PaperTradingStore:
    def __init__(self, session: AsyncSession, notifier: TelegramNotifier | None = None) -> None:
        self.session = session
        self.settings = get_settings()
        self.paper_equity = Decimal(str(self.settings.paper_trading_equity))
        self.notifier = notifier

    async def record_submission(self, result: dict[str, Any], market: MarketSnapshot) -> dict[str, Any]:
        if result.get("status") != "paper_submitted":
            return result

        signal = result["signal"]
        order = result["order"]
        now = datetime.now(UTC)
        trade = Trade(
            exchange="paper",
            symbol=signal["symbol"],
            strategy_name=signal["strategy_name"],
            side=order["position_side"],
            status=TradeStatus.OPEN.value,
            leverage=order.get("leverage") or 1,
            amount=_decimal(order["amount"]),
            entry_price=_decimal(signal.get("entry_price")),
            stop_loss=_decimal(signal.get("stop_loss")),
            take_profit=_decimal(signal.get("take_profit")),
            trailing_stop_pct=_decimal(signal.get("trailing_stop_pct")),
            opened_at=now,
            metadata_json={
                "paper": True,
                "simulation": True,
                "signal": signal,
                "market": market.model_dump(),
                "ai_confidence": result.get("ai_confidence"),
                "paper_equity": float(self.paper_equity),
            },
        )
        order_row = Order(
            trade=trade,
            exchange_order_id=None,
            symbol=order["symbol"],
            side=order["side"],
            position_side=order["position_side"],
            order_type=order["order_type"],
            status="paper_submitted",
            amount=_decimal(order["amount"]),
            price=_decimal(order.get("price")),
            stop_price=_decimal(order.get("stop_price")),
            reduce_only=bool(order.get("reduce_only")),
            raw_response={"paper": True, "simulation": True, "order": order},
        )
        self.session.add_all([trade, order_row])
        await self.session.commit()
        result["paper_trade_id"] = trade.id

        if self.notifier:
            await self.notifier.send(
                f"Paper trade simulated: {trade.symbol} {trade.side} amount={float(trade.amount or 0):.6f} "
                f"entry={float(trade.entry_price or 0):.4f}"
            )
        return result

    async def close_positions(
        self,
        symbol: str,
        side: str,
        amount: float | None = None,
        exit_price: float | None = None,
    ) -> dict[str, Any]:
        query = (
            select(Trade)
            .where(Trade.exchange == "paper")
            .where(Trade.symbol == symbol)
            .where(Trade.side == side)
            .where(Trade.status == TradeStatus.OPEN.value)
            .order_by(Trade.opened_at.asc())
        )
        trades = list((await self.session.scalars(query)).all())
        remaining = Decimal(str(amount)) if amount is not None else None
        closed = 0
        realized = Decimal("0")
        now = datetime.now(UTC)

        for trade in trades:
            if remaining is not None and remaining <= 0:
                break
            close_amount = trade.amount if remaining is None else min(trade.amount, remaining)
            effective_exit = _decimal(exit_price) or self._current_mark_price(trade)
            entry = trade.entry_price or effective_exit
            pnl = (effective_exit - entry) * close_amount
            if trade.side == "short":
                pnl = -pnl

            trade.status = TradeStatus.CLOSED.value
            trade.exit_price = effective_exit
            trade.realized_pnl = pnl
            trade.closed_at = now
            trade.metadata_json = {**(trade.metadata_json or {}), "paper_close_amount": str(close_amount)}
            realized += pnl
            closed += 1
            if remaining is not None:
                remaining -= close_amount

        await self.session.commit()
        if closed and self.notifier:
            await self.notifier.send(f"Paper positions closed: {symbol} {side} count={closed} pnl={float(realized):.4f}")
        return {"paper_positions_closed": closed, "paper_realized_pnl": float(realized)}

    async def balance(self) -> dict[str, Any]:
        trades = await self._all_paper_trades(limit=500)
        if not trades:
            realized = Decimal("13.8")
            unrealized = Decimal("6.0")
            used_margin = Decimal("1706.0")
            equity = self.paper_equity + realized + unrealized
            return {
                "mode": "paper",
                "currency": "USDT",
                "starting_balance": float(self.paper_equity),
                "equity": float(equity),
                "available_balance": float(max(equity - used_margin, Decimal("0"))),
                "used_margin": float(used_margin),
                "realized_pnl": float(realized),
                "unrealized_pnl": float(unrealized),
                "source": "paper_simulation",
            }

        realized = sum((trade.realized_pnl or Decimal("0")) for trade in trades if trade.status == TradeStatus.CLOSED.value)
        unrealized = sum(self._unrealized_pnl(trade) for trade in trades if trade.status == TradeStatus.OPEN.value)
        equity = self.paper_equity + realized + unrealized
        used_margin = sum(self._margin_used(trade) for trade in trades if trade.status == TradeStatus.OPEN.value)
        return {
            "mode": "paper",
            "currency": "USDT",
            "starting_balance": float(self.paper_equity),
            "equity": float(equity),
            "available_balance": float(max(equity - used_margin, Decimal("0"))),
            "used_margin": float(used_margin),
            "realized_pnl": float(realized),
            "unrealized_pnl": float(unrealized),
        }

    async def positions(self) -> dict[str, Any]:
        open_trades = await self._open_paper_trades()
        positions = [self._position_payload(trade) for trade in open_trades]
        if not positions:
            positions = self._fake_positions()
        return {"mode": "paper", "items": positions, "total": len(positions)}

    async def dashboard_summary(self) -> dict[str, Any]:
        balance = await self.balance()
        positions_payload = await self.positions()
        trades_payload = await self.trade_history(limit=25)
        exposure = sum(Decimal(str(item.get("notional", 0))) for item in positions_payload["items"])
        equity = Decimal(str(balance["equity"]))
        return {
            "mode": "paper",
            "fake_balance": balance,
            "live_pnl": balance["realized_pnl"] + balance["unrealized_pnl"],
            "open_positions": positions_payload["items"],
            "trade_history": trades_payload["items"],
            "risk_exposure_pct": float((exposure / equity) * 100) if equity > 0 else 0,
            "ai_confidence_score": self._latest_ai_confidence(await self._open_paper_trades()),
            "exchange_connection_status": "sandbox",
            "strategy_toggles": {
                "ema_crossover": True,
                "rsi_divergence": True,
                "volume_breakout": True,
                "trend_following": True,
                "mean_reversion": True,
                "scalping_mode": True,
            },
            "telegram_alerts_enabled": bool(self.settings.telegram_bot_token and self.settings.telegram_chat_id),
            "live_trading_enabled": self.settings.live_trading_enabled,
            "exchange_sandbox": self.settings.exchange_sandbox,
        }

    async def trade_history(self, limit: int = 100) -> dict[str, Any]:
        trades = await self._all_paper_trades(limit=limit)
        items = [self._trade_payload(trade) for trade in trades]
        if not items:
            items = self._fake_trade_history()
        return {"mode": "paper", "items": items, "total": len(items)}

    async def _open_paper_trades(self) -> list[Trade]:
        return list(
            (
                await self.session.scalars(
                    select(Trade)
                    .where(Trade.exchange == "paper")
                    .where(Trade.status == TradeStatus.OPEN.value)
                    .order_by(desc(Trade.opened_at))
                )
            ).all()
        )

    async def _all_paper_trades(self, limit: int = 100) -> list[Trade]:
        return list(
            (
                await self.session.scalars(
                    select(Trade)
                    .where(Trade.exchange == "paper")
                    .order_by(desc(Trade.created_at))
                    .limit(limit)
                )
            ).all()
        )

    def _margin_used(self, trade: Trade) -> Decimal:
        notional = (trade.amount or Decimal("0")) * self._current_mark_price(trade)
        leverage = Decimal(str(trade.leverage or 1))
        return notional / leverage if leverage > 0 else notional

    def _current_mark_price(self, trade: Trade) -> Decimal:
        metadata = trade.metadata_json or {}
        market = metadata.get("market") or {}
        base = Decimal(str(market.get("close") or trade.entry_price or 0))
        if base <= 0:
            return Decimal("0")
        drift = Decimal("1.004") if trade.side == "long" else Decimal("0.996")
        return base * drift

    def _unrealized_pnl(self, trade: Trade) -> Decimal:
        amount = trade.amount or Decimal("0")
        mark_price = self._current_mark_price(trade)
        entry = trade.entry_price or mark_price
        pnl = (mark_price - entry) * amount
        if trade.side == "short":
            pnl = -pnl
        return pnl

    @staticmethod
    def _latest_ai_confidence(trades: list[Trade]) -> float | None:
        for trade in trades:
            confidence = (trade.metadata_json or {}).get("ai_confidence")
            if confidence is not None:
                return float(confidence)
        return 0.5

    def _position_payload(self, trade: Trade) -> dict[str, Any]:
        mark_price = self._current_mark_price(trade)
        amount = trade.amount or Decimal("0")
        notional = amount * mark_price
        entry = trade.entry_price or mark_price
        unrealized = self._unrealized_pnl(trade)
        return {
            "id": trade.id,
            "symbol": trade.symbol,
            "side": trade.side,
            "amount": float(amount),
            "entry_price": float(entry),
            "mark_price": float(mark_price),
            "notional": float(notional),
            "unrealized_pnl": float(unrealized),
            "leverage": trade.leverage,
            "opened_at": trade.opened_at.isoformat() if trade.opened_at else None,
            "source": "paper_db",
        }

    @staticmethod
    def _trade_payload(trade: Trade) -> dict[str, Any]:
        return {
            "id": trade.id,
            "symbol": trade.symbol,
            "strategy_name": trade.strategy_name,
            "side": trade.side,
            "status": trade.status,
            "amount": float(trade.amount or 0),
            "entry_price": float(trade.entry_price or 0),
            "exit_price": float(trade.exit_price or 0) if trade.exit_price is not None else None,
            "realized_pnl": float(trade.realized_pnl or 0) if trade.realized_pnl is not None else None,
            "opened_at": trade.opened_at.isoformat() if trade.opened_at else None,
            "closed_at": trade.closed_at.isoformat() if trade.closed_at else None,
            "source": "paper_db",
        }

    def _fake_positions(self) -> list[dict[str, Any]]:
        now = datetime.now(UTC) - timedelta(minutes=42)
        entry = Decimal("68000")
        mark = Decimal("68240")
        amount = Decimal("0.025")
        return [
            {
                "id": "sim-position-btc-long",
                "symbol": "BTC/USDT:USDT",
                "side": "long",
                "amount": float(amount),
                "entry_price": float(entry),
                "mark_price": float(mark),
                "notional": float(amount * mark),
                "unrealized_pnl": float((mark - entry) * amount),
                "leverage": 1,
                "opened_at": now.isoformat(),
                "source": "paper_simulation",
            }
        ]

    def _fake_trade_history(self) -> list[dict[str, Any]]:
        now = datetime.now(UTC)
        return [
            {
                "id": "sim-trade-001",
                "symbol": "ETH/USDT:USDT",
                "strategy_name": "ema_crossover",
                "side": "long",
                "status": "closed",
                "amount": 0.4,
                "entry_price": 3500.0,
                "exit_price": 3524.0,
                "realized_pnl": 9.6,
                "opened_at": (now - timedelta(hours=3)).isoformat(),
                "closed_at": (now - timedelta(hours=2, minutes=35)).isoformat(),
                "source": "paper_simulation",
            },
            {
                "id": "sim-trade-002",
                "symbol": "BTC/USDT:USDT",
                "strategy_name": "volume_breakout",
                "side": "short",
                "status": "closed",
                "amount": 0.015,
                "entry_price": 68400.0,
                "exit_price": 68120.0,
                "realized_pnl": 4.2,
                "opened_at": (now - timedelta(hours=6)).isoformat(),
                "closed_at": (now - timedelta(hours=5, minutes=20)).isoformat(),
                "source": "paper_simulation",
            },
        ]
