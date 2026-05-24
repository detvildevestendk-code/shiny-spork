import logging
from statistics import mean
from typing import Any

from app.intelligence.schemas import IntelligenceSignal, MarketIntelligenceSnapshot

logger = logging.getLogger(__name__)


def clamp(value: float, low: float = -100, high: float = 100) -> float:
    return max(min(value, high), low)


def average_score(signals: list[IntelligenceSignal], source: str) -> float:
    values = [signal.score for signal in signals if signal.source == source]
    return clamp(mean(values)) if values else 0


class MarketIntelligenceScorer:
    def score(
        self,
        signals: list[IntelligenceSignal],
        market_breakdown: dict[str, Any],
        futures_breakdown: dict[str, Any],
        watched_accounts_status: list[dict[str, Any]],
    ) -> MarketIntelligenceSnapshot:
        market_trend_score = average_score(signals, "market_data")
        futures_pressure_score = average_score(signals, "futures_data")
        social_influence_score = average_score(signals, "social_monitor")
        news_risk_score = average_score(signals, "news_monitor")
        whale_flow_score = average_score(signals, "whale_monitor")
        sentiment_score = self._sentiment_score(market_breakdown, news_risk_score)
        weighted = (
            market_trend_score * 0.28
            + futures_pressure_score * 0.22
            + sentiment_score * 0.15
            + social_influence_score * 0.12
            + news_risk_score * 0.15
            + whale_flow_score * 0.08
        )
        risk_penalty = max(abs(news_risk_score) - 35, 0) * 0.25
        confidence = max(min(50 + weighted / 2 - risk_penalty, 100), 0)
        blocked_reasons: list[str] = []
        if news_risk_score < -60:
            blocked_reasons.append("High news risk: pause paper trade generation")
        if any((item.get("volatility_pct") or 0) > 8 for item in market_breakdown.get("symbols", {}).values() if isinstance(item, dict)):
            blocked_reasons.append("Extreme volatility detected")
        if confidence < 55:
            blocked_reasons.append("Market intelligence confidence below threshold")
        latest_social = [s.model_dump(mode="json") for s in signals if s.source == "social_monitor"][:10]
        latest_news = [s.model_dump(mode="json") for s in signals if s.source == "news_monitor"][:10]
        latest_whale = [s.model_dump(mode="json") for s in signals if s.source == "whale_monitor"][:10]
        reasoning = (
            f"Market={market_trend_score:.1f}, Futures={futures_pressure_score:.1f}, "
            f"Sentiment={sentiment_score:.1f}, Social={social_influence_score:.1f}, "
            f"NewsRisk={news_risk_score:.1f}, Whale={whale_flow_score:.1f}, Confidence={confidence:.1f}"
        )
        logger.info("Market intelligence score update: %s", reasoning)
        for signal in signals:
            if signal.source in {"social_monitor", "news_monitor", "whale_monitor"}:
                logger.info("%s signal detected: %s", signal.source, signal.message)
        for reason in blocked_reasons:
            logger.warning("Blocked trade reason: %s", reason)
        return MarketIntelligenceSnapshot(
            market_trend_score=market_trend_score,
            futures_pressure_score=futures_pressure_score,
            sentiment_score=sentiment_score,
            social_influence_score=social_influence_score,
            news_risk_score=news_risk_score,
            whale_flow_score=whale_flow_score,
            final_ai_confidence_score=confidence,
            market_intelligence_score=confidence,
            latest_social_signals=latest_social,
            latest_news_signals=latest_news,
            latest_whale_signals=latest_whale,
            latest_ai_reasoning=reasoning,
            blocked_trade_reasons=blocked_reasons,
            watched_accounts_status=watched_accounts_status,
            sentiment_breakdown={
                "crypto_fear_greed": "placeholder_provider_required",
                "coinmarketcap_fear_greed": "placeholder_provider_required",
                "btc_dominance": "placeholder_provider_required",
                "market_cap_change": "placeholder_provider_required",
                "altcoin_rotation": "placeholder_provider_required",
                "score": sentiment_score,
            },
            futures_breakdown=futures_breakdown,
            market_breakdown=market_breakdown,
        )

    @staticmethod
    def _sentiment_score(market_breakdown: dict[str, Any], news_risk_score: float) -> float:
        market_scores = [item.get("score", 0) for item in market_breakdown.get("symbols", {}).values() if isinstance(item, dict)]
        base = mean(market_scores) if market_scores else 0
        return clamp(base * 0.35 + news_risk_score * 0.2)
