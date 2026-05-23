from app.strategies.base import Strategy
from app.strategies.ema_crossover import EmaCrossoverStrategy
from app.strategies.mean_reversion import MeanReversionStrategy
from app.strategies.rsi_divergence import RsiDivergenceStrategy
from app.strategies.scalping_mode import ScalpingModeStrategy
from app.strategies.trend_following import TrendFollowingStrategy
from app.strategies.volume_breakout import VolumeBreakoutStrategy


class StrategyRegistry:
    def __init__(self) -> None:
        self._strategies: dict[str, Strategy] = {}

    def register(self, strategy: Strategy) -> None:
        self._strategies[strategy.name] = strategy

    def get(self, name: str) -> Strategy:
        return self._strategies[name]

    def all(self) -> list[Strategy]:
        return list(self._strategies.values())


def build_default_registry() -> StrategyRegistry:
    registry = StrategyRegistry()
    registry.register(EmaCrossoverStrategy())
    registry.register(RsiDivergenceStrategy())
    registry.register(VolumeBreakoutStrategy())
    registry.register(TrendFollowingStrategy())
    registry.register(MeanReversionStrategy())
    registry.register(ScalpingModeStrategy())
    return registry
