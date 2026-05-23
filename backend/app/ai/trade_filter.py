from app.ai.client import OpenAiMarketAnalyzer
from app.ai.schemas import AiAnalysisRequest
from app.core.config import Settings
from app.trading.schemas import MarketSnapshot, StrategySignal, TradeDecision


class AiTradeFilter:
    def __init__(self, analyzer: OpenAiMarketAnalyzer, settings: Settings) -> None:
        self.analyzer = analyzer
        self.settings = settings

    async def evaluate(
        self,
        signal: StrategySignal,
        market: MarketSnapshot,
        recent_news: list[str] | None = None,
    ) -> TradeDecision:
        if not self.settings.ai_filter_enabled:
            return TradeDecision(allowed=True, reason="AI filter disabled")

        result = await self.analyzer.analyze(
            AiAnalysisRequest(signal=signal, market=market, recent_news=recent_news or [])
        )
        if not result.allowed:
            return TradeDecision(
                allowed=False,
                reason="AI blocked trade: " + "; ".join(result.reasons),
                ai_confidence=result.confidence,
            )
        if result.confidence < self.settings.ai_min_confidence:
            return TradeDecision(
                allowed=False,
                reason="AI confidence below minimum threshold",
                ai_confidence=result.confidence,
            )
        return TradeDecision(
            allowed=True,
            reason="AI filter passed",
            ai_confidence=result.confidence,
        )
