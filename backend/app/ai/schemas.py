from pydantic import BaseModel, Field

from app.trading.schemas import MarketSnapshot, StrategySignal


class AiAnalysisRequest(BaseModel):
    signal: StrategySignal
    market: MarketSnapshot
    recent_news: list[str] = Field(default_factory=list)


class AiAnalysisResult(BaseModel):
    allowed: bool
    confidence: float = Field(ge=0, le=1)
    sentiment: str
    volatility_risk: str
    news_risk: str
    reasons: list[str]
