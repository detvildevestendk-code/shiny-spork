from app.intelligence.schemas import IntelligenceSignal


class NewsMonitorAdapter:
    async def collect(self) -> list[IntelligenceSignal]:
        sources = ["CoinDesk", "CoinTelegraph", "The Block", "Decrypt", "Binance announcements", "Bybit announcements", "OKX announcements", "SEC", "Federal Reserve", "ETF analysts"]
        return [
            IntelligenceSignal(source="news_monitor", signal_type="mock_news_risk", asset="MARKET", direction="neutral", score=0, confidence=0.3, message="News adapter placeholder active; connect RSS/API provider for production signals", metadata={"monitored_sources": sources}),
            IntelligenceSignal(source="news_monitor", signal_type="risk_watch", asset="MARKET", direction="risk", score=-10, confidence=0.4, message="Monitoring for hacks, exploits, regulation, ETF and exchange outage news", metadata={"mock": True}),
        ]
