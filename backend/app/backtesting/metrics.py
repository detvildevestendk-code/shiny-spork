import math
from dataclasses import dataclass

import pandas as pd


@dataclass
class BacktestMetrics:
    total_trades: int
    win_rate: float
    net_pnl: float
    max_drawdown: float
    sharpe_ratio: float


def calculate_metrics(trades: pd.DataFrame, equity_curve: pd.Series) -> BacktestMetrics:
    if trades.empty:
        return BacktestMetrics(0, 0, 0, 0, 0)

    pnl = trades["pnl"].astype(float)
    wins = pnl[pnl > 0].count()
    returns = equity_curve.pct_change().dropna()
    sharpe = 0.0
    if not returns.empty and returns.std() != 0:
        sharpe = math.sqrt(365) * returns.mean() / returns.std()

    running_max = equity_curve.cummax()
    drawdown = (equity_curve - running_max) / running_max
    return BacktestMetrics(
        total_trades=len(trades),
        win_rate=float(wins / len(trades)),
        net_pnl=float(pnl.sum()),
        max_drawdown=float(abs(drawdown.min())),
        sharpe_ratio=float(sharpe),
    )
