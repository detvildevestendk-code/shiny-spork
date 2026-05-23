import json
import logging

from openai import AsyncOpenAI

from app.ai.schemas import AiAnalysisRequest, AiAnalysisResult
from app.core.config import Settings

logger = logging.getLogger(__name__)


class OpenAiMarketAnalyzer:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.client = AsyncOpenAI(api_key=settings.openai_api_key) if settings.openai_api_key else None

    async def analyze(self, request: AiAnalysisRequest) -> AiAnalysisResult:
        if not self.client:
            return AiAnalysisResult(
                allowed=True,
                confidence=0.5,
                sentiment="unknown",
                volatility_risk="unknown",
                news_risk="unknown",
                reasons=["OpenAI API key not configured; neutral pass-through analysis used."],
            )

        prompt = self._build_prompt(request)
        response = await self.client.responses.create(
            model=self.settings.openai_model,
            input=prompt,
            text={"format": {"type": "json_object"}},
        )
        try:
            payload = json.loads(response.output_text)
            return AiAnalysisResult.model_validate(payload)
        except Exception as exc:
            logger.exception("Failed to parse AI response: %s", exc)
            return AiAnalysisResult(
                allowed=False,
                confidence=0,
                sentiment="unknown",
                volatility_risk="unknown",
                news_risk="unknown",
                reasons=["AI response parsing failed; blocking trade safely."],
            )

    @staticmethod
    def _build_prompt(request: AiAnalysisRequest) -> str:
        return (
            "You are a crypto futures risk analyst. You may only block or pass a proposed trade; "
            "you must not increase leverage, change stops, or override risk rules. Return JSON with "
            "allowed, confidence, sentiment, volatility_risk, news_risk, and reasons.\n\n"
            f"Signal: {request.signal.model_dump_json()}\n"
            f"Market: {request.market.model_dump_json()}\n"
            f"Recent news headlines: {json.dumps(request.recent_news)}"
        )
