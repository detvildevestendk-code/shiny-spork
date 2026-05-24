import logging
from statistics import mean
from typing import Any

import httpx

from app.intelligence.schemas import IntelligenceSignal

logger = logging.getLogger(__name__)

BINANCE_BASE = "https://fapi.binance.com"
SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]


class MarketDataAdapter:
    async def collect(self) -> tuple[list[IntelligenceSignal], dict[str, Any]]:
        signals: list[IntelligenceSignal] = []
        breakdown: dict[str, Any] = {"symbols": {}}
        async with httpx.AsyncClient(timeout=8) as client:
            for symbol in SYMBOLS:
                try:
                    response = await client.get(f"{BINANCE_BASE}/fapi/v1/klines", params={"symbol": symbol, "interval": "15m", "limit": 80})
                    response.raise_for_status()
                    candles = response.json()
                    if not isinstance(candles, list) or not candles or not isinstance(candles[0], list):
                        raise ValueError(f"unexpected kline payload: {str(candles)[:120]}")
                    closes = [float(candle[4]) for candle in candles]
                    volumes = [float(candle[5]) for candle in candles]
                    if len(closes) < 30:
                        raise ValueError("not enough candle data")
                    ema_fast = self._ema(closes, 12)
                    ema_slow = self._ema(closes, 26)
                    rsi = self._rsi(closes)
                    volatility = (max(closes[-20:]) - min(closes[-20:])) / closes[-1] * 100
                    volume_change = ((volumes[-1] - mean(volumes[-20:-1])) / max(mean(volumes[-20:-1]), 1)) * 100
                    trend_score = max(min((ema_fast - ema_slow) / closes[-1] * 10000, 100), -100)
                    if rsi > 70:
                        trend_score -= 15
                    elif rsi < 30:
                        trend_score += 15
                    breakdown["symbols"][symbol] = {
                        "price": closes[-1],
                        "ema_fast": ema_fast,
                        "ema_slow": ema_slow,
                        "rsi": rsi,
                        "macd": ema_fast - ema_slow,
                        "volatility_pct": volatility,
                        "volume_change_pct": volume_change,
                        "support": min(closes[-30:]),
                        "resistance": max(closes[-30:]),
                        "score": trend_score,
                    }
                    signals.append(IntelligenceSignal(source="market_data", signal_type="trend", asset=symbol.replace("USDT", ""), direction="bullish" if trend_score > 0 else "bearish", score=trend_score, confidence=0.7, message=f"{symbol} EMA/RSI market trend score {trend_score:.1f}"))
                except Exception as exc:
                    logger.warning("Market data adapter failed for %s: %s", symbol, exc)
                    breakdown["symbols"][symbol] = {
                        "error": str(exc),
                        "price": None,
                        "ema_fast": None,
                        "ema_slow": None,
                        "rsi": None,
                        "macd": None,
                        "volatility_pct": 0,
                        "volume_change_pct": 0,
                        "support": None,
                        "resistance": None,
                        "score": 0,
                    }
        return signals, breakdown

    @staticmethod
    def _ema(values: list[float], period: int) -> float:
        multiplier = 2 / (period + 1)
        ema = values[0]
        for value in values[1:]:
            ema = (value - ema) * multiplier + ema
        return ema

    @staticmethod
    def _rsi(values: list[float], period: int = 14) -> float:
        gains: list[float] = []
        losses: list[float] = []
        for prev, cur in zip(values[-period - 1:-1], values[-period:]):
            delta = cur - prev
            gains.append(max(delta, 0))
            losses.append(abs(min(delta, 0)))
        avg_gain = mean(gains) if gains else 0
        avg_loss = mean(losses) if losses else 0
        if avg_loss == 0:
            return 100
        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))
