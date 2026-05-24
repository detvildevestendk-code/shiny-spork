import logging

from app.intelligence.futures_data import FuturesDataAdapter
from app.intelligence.market_data import MarketDataAdapter
from app.intelligence.news_monitor import NewsMonitorAdapter
from app.intelligence.scoring import MarketIntelligenceScorer
from app.intelligence.schemas import MarketIntelligenceSnapshot
from app.intelligence.social_monitor import SocialMonitorAdapter
from app.intelligence.whale_monitor import WhaleMonitorAdapter

logger = logging.getLogger(__name__)


class MarketIntelligenceService:
    def __init__(self) -> None:
        self.market_adapter = MarketDataAdapter()
        self.futures_adapter = FuturesDataAdapter()
        self.social_adapter = SocialMonitorAdapter()
        self.news_adapter = NewsMonitorAdapter()
        self.whale_adapter = WhaleMonitorAdapter()
        self.scorer = MarketIntelligenceScorer()

    async def snapshot(self) -> MarketIntelligenceSnapshot:
        signals = []
        market_breakdown = {"symbols": {}}
        futures_breakdown = {"symbols": {}}
        watched_accounts_status = []
        try:
            market_signals, market_breakdown = await self.market_adapter.collect()
            signals.extend(market_signals)
        except Exception as exc:
            logger.warning("Market intelligence market adapter failed: %s", exc)
        try:
            futures_signals, futures_breakdown = await self.futures_adapter.collect()
            signals.extend(futures_signals)
        except Exception as exc:
            logger.warning("Market intelligence futures adapter failed: %s", exc)
        try:
            social_signals, watched_accounts_status = await self.social_adapter.collect()
            signals.extend(social_signals)
        except Exception as exc:
            logger.warning("Market intelligence social adapter failed: %s", exc)
        try:
            signals.extend(await self.news_adapter.collect())
        except Exception as exc:
            logger.warning("Market intelligence news adapter failed: %s", exc)
        try:
            signals.extend(await self.whale_adapter.collect())
        except Exception as exc:
            logger.warning("Market intelligence whale adapter failed: %s", exc)
        snapshot = self.scorer.score(signals, market_breakdown, futures_breakdown, watched_accounts_status)
        logger.info("AI reasoning for paper decision context: %s", snapshot.latest_ai_reasoning)
        return snapshot
