from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class IntelligenceSignal(BaseModel):
    source: str
    signal_type: str
    asset: str = "MARKET"
    direction: Literal["bullish", "bearish", "neutral", "risk"] = "neutral"
    score: float = Field(ge=-100, le=100)
    confidence: float = Field(default=0.5, ge=0, le=1)
    message: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    detected_at: datetime = Field(default_factory=datetime.utcnow)


class MarketIntelligenceSnapshot(BaseModel):
    market_trend_score: float = Field(ge=-100, le=100)
    futures_pressure_score: float = Field(ge=-100, le=100)
    sentiment_score: float = Field(ge=-100, le=100)
    social_influence_score: float = Field(ge=-100, le=100)
    news_risk_score: float = Field(ge=-100, le=100)
    whale_flow_score: float = Field(ge=-100, le=100)
    final_ai_confidence_score: float = Field(ge=0, le=100)
    market_intelligence_score: float = Field(ge=0, le=100)
    latest_social_signals: list[dict[str, Any]] = Field(default_factory=list)
    latest_news_signals: list[dict[str, Any]] = Field(default_factory=list)
    latest_whale_signals: list[dict[str, Any]] = Field(default_factory=list)
    latest_ai_reasoning: str
    blocked_trade_reasons: list[str] = Field(default_factory=list)
    watched_accounts_status: list[dict[str, Any]] = Field(default_factory=list)
    sentiment_breakdown: dict[str, Any] = Field(default_factory=dict)
    futures_breakdown: dict[str, Any] = Field(default_factory=dict)
    market_breakdown: dict[str, Any] = Field(default_factory=dict)
    generated_at: datetime = Field(default_factory=datetime.utcnow)
