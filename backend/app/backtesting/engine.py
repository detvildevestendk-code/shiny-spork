from pathlib import Path

import pandas as pd

from app.backtesting.metrics import BacktestMetrics, calculate_metrics
from app.strategies.base import Strategy
from app.trading.enums import SignalAction


class BacktestEngine:
    def __init__(self, starting_equity: float = 10_000, fee_pct: float = 0.04) -> None:
        self.starting_equity = starting_equity
        self.fee_pct = fee_pct

    def run(self, symbol: str, candles: pd.DataFrame, strategy: Strategy) -> tuple[pd.DataFrame, BacktestMetrics]:
        equity = self.starting_equity
        open_trade: dict | None = None
        trades: list[dict] = []
        equity_points: list[float] = [equity]

        for index in range(50, len(candles)):
            window = candles.iloc[: index + 1]
            signal = strategy.generate_signal(symbol, window)
            price = float(window["close"].iloc[-1])

            if open_trade:
                should_close = self._should_close(open_trade, price)
                if should_close:
                    pnl = self._pnl(open_trade, price)
                    fee = abs(open_trade["amount"] * price) * (self.fee_pct / 100)
                    equity += pnl - fee
                    trades.append({**open_trade, "exit_price": price, "pnl": pnl - fee, "exit_index": index})
                    open_trade = None

            if open_trade is None and signal.action in {SignalAction.OPEN_LONG, SignalAction.OPEN_SHORT}:
                amount = equity * 0.01 / abs((signal.entry_price or price) - (signal.stop_loss or price * 0.99))
                open_trade = {
                    "symbol": symbol,
                    "side": "long" if signal.action == SignalAction.OPEN_LONG else "short",
                    "entry_price": signal.entry_price or price,
                    "stop_loss": signal.stop_loss,
                    "take_profit": signal.take_profit,
                    "amount": amount,
                    "entry_index": index,
                    "strategy_name": strategy.name,
                }

            equity_points.append(equity)

        trades_df = pd.DataFrame(trades)
        equity_curve = pd.Series(equity_points)
        return trades_df, calculate_metrics(trades_df, equity_curve)

    @staticmethod
    def export_csv(trades: pd.DataFrame, path: str | Path) -> None:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        trades.to_csv(path, index=False)

    @staticmethod
    def _should_close(trade: dict, price: float) -> bool:
        if trade["side"] == "long":
            return price <= trade["stop_loss"] or price >= trade["take_profit"]
        return price >= trade["stop_loss"] or price <= trade["take_profit"]

    @staticmethod
    def _pnl(trade: dict, exit_price: float) -> float:
        if trade["side"] == "long":
            return (exit_price - trade["entry_price"]) * trade["amount"]
        return (trade["entry_price"] - exit_price) * trade["amount"]
