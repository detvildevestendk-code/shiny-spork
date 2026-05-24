import json
import logging
from pathlib import Path
from typing import Any

from app.intelligence.schemas import IntelligenceSignal

logger = logging.getLogger(__name__)
WATCHLIST_PATH = Path(__file__).parent / "watchlists" / "social_accounts.json"


class SocialMonitorAdapter:
    def load_watchlist(self) -> list[dict[str, Any]]:
        try:
            return json.loads(WATCHLIST_PATH.read_text())
        except Exception as exc:
            logger.warning("Failed to load social watchlist: %s", exc)
            return []

    async def collect(self) -> tuple[list[IntelligenceSignal], list[dict[str, Any]]]:
        watchlist = self.load_watchlist()
        signals: list[IntelligenceSignal] = []
        for account in watchlist[:5]:
            risk_level = account.get("risk_level", "medium")
            score = -15 if risk_level == "high" else 5
            signals.append(IntelligenceSignal(source="social_monitor", signal_type="mock_social_watch", asset="MARKET", direction="risk" if score < 0 else "neutral", score=score, confidence=0.35, message=f"Mock X/Twitter adapter active for @{account.get('handle')}; official API credentials not configured", metadata={"account": account}))
        status = [{"handle": item.get("handle"), "name": item.get("name"), "category": item.get("category"), "status": "mock_adapter", "influence_score": item.get("influence_score"), "risk_level": item.get("risk_level")} for item in watchlist]
        return signals, status
