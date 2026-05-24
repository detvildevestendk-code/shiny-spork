from app.intelligence.schemas import IntelligenceSignal


class WhaleMonitorAdapter:
    async def collect(self) -> list[IntelligenceSignal]:
        return [
            IntelligenceSignal(source="whale_monitor", signal_type="mock_whale_flow", asset="MARKET", direction="neutral", score=0, confidence=0.25, message="Whale flow placeholder active for BTC/ETH/SOL transfers, exchange inflows/outflows, and stablecoin mint/burn", metadata={"providers": ["Whale Alert", "exchange flow provider", "stablecoin mint/burn feed"]})
        ]
