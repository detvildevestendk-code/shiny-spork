import logging
from typing import Any

import httpx

from app.intelligence.schemas import IntelligenceSignal

logger = logging.getLogger(__name__)
BINANCE_BASE = "https://fapi.binance.com"
BYBIT_BASE = "https://api.bybit.com"
SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]


class FuturesDataAdapter:
    async def collect(self) -> tuple[list[IntelligenceSignal], dict[str, Any]]:
        signals: list[IntelligenceSignal] = []
        breakdown: dict[str, Any] = {"symbols": {}}
        async with httpx.AsyncClient(timeout=8) as client:
            for symbol in SYMBOLS:
                bybit_public = await self._collect_bybit_public(client, symbol)
                try:
                    funding_response = await client.get(f"{BINANCE_BASE}/fapi/v1/fundingRate", params={"symbol": symbol, "limit": 1})
                    oi_response = await client.get(f"{BINANCE_BASE}/fapi/v1/openInterest", params={"symbol": symbol})
                    ticker_response = await client.get(f"{BINANCE_BASE}/fapi/v1/premiumIndex", params={"symbol": symbol})
                    orderbook_response = await client.get(f"{BINANCE_BASE}/fapi/v1/depth", params={"symbol": symbol, "limit": 20})
                    for response in (funding_response, oi_response, ticker_response, orderbook_response):
                        response.raise_for_status()
                    funding_payload = funding_response.json()
                    if not isinstance(funding_payload, list) or not funding_payload:
                        raise ValueError(f"unexpected funding payload: {str(funding_payload)[:120]}")
                    funding = funding_payload[0]
                    oi = oi_response.json()
                    ticker = ticker_response.json()
                    orderbook = orderbook_response.json()
                    bid_notional = sum(float(price) * float(qty) for price, qty in orderbook.get("bids", []))
                    ask_notional = sum(float(price) * float(qty) for price, qty in orderbook.get("asks", []))
                    imbalance = (bid_notional - ask_notional) / max(bid_notional + ask_notional, 1) * 100
                    funding_rate = float(funding.get("fundingRate", 0)) * 100
                    mark = float(ticker.get("markPrice", 0))
                    index = float(ticker.get("indexPrice", mark or 1))
                    premium = (mark - index) / max(index, 1) * 100
                    score = max(min(imbalance - funding_rate * 10 + premium * 5, 100), -100)
                    breakdown["symbols"][symbol] = {
                        "funding_rate_pct": funding_rate,
                        "open_interest": float(oi.get("openInterest", 0)),
                        "mark_price": mark,
                        "index_price": index,
                        "mark_index_premium_pct": premium,
                        "orderbook_imbalance_pct": imbalance,
                        "liquidation_spike": "placeholder_public_feed_required",
                        "long_short_ratio": "placeholder_public_feed_required",
                        "score": score,
                        "bybit_public": bybit_public,
                    }
                    signals.append(IntelligenceSignal(source="futures_data", signal_type="pressure", asset=symbol.replace("USDT", ""), direction="bullish" if score > 0 else "bearish", score=score, confidence=0.65, message=f"{symbol} futures pressure score {score:.1f}"))
                except Exception as exc:
                    logger.warning("Futures data adapter failed for %s: %s", symbol, exc)
                    breakdown["symbols"][symbol] = {
                        "error": str(exc),
                        "funding_rate_pct": 0,
                        "open_interest": None,
                        "mark_price": None,
                        "index_price": None,
                        "mark_index_premium_pct": 0,
                        "orderbook_imbalance_pct": 0,
                        "liquidation_spike": "placeholder_public_feed_required",
                        "long_short_ratio": "placeholder_public_feed_required",
                        "score": 0,
                        "bybit_public": bybit_public,
                    }
        return signals, breakdown

    async def _collect_bybit_public(self, client: httpx.AsyncClient, symbol: str) -> dict[str, Any]:
        try:
            ticker_response = await client.get(f"{BYBIT_BASE}/v5/market/tickers", params={"category": "linear", "symbol": symbol})
            orderbook_response = await client.get(f"{BYBIT_BASE}/v5/market/orderbook", params={"category": "linear", "symbol": symbol, "limit": 25})
            funding_response = await client.get(f"{BYBIT_BASE}/v5/market/funding/history", params={"category": "linear", "symbol": symbol, "limit": 1})
            for response in (ticker_response, orderbook_response, funding_response):
                response.raise_for_status()
            ticker = (ticker_response.json().get("result", {}).get("list") or [{}])[0]
            orderbook = orderbook_response.json().get("result", {})
            funding = (funding_response.json().get("result", {}).get("list") or [{}])[0]
            bids = orderbook.get("b", [])
            asks = orderbook.get("a", [])
            bid_notional = sum(float(price) * float(qty) for price, qty in bids)
            ask_notional = sum(float(price) * float(qty) for price, qty in asks)
            imbalance = (bid_notional - ask_notional) / max(bid_notional + ask_notional, 1) * 100
            return {
                "mark_price": float(ticker.get("markPrice") or 0),
                "index_price": float(ticker.get("indexPrice") or 0),
                "funding_rate_pct": float(funding.get("fundingRate") or ticker.get("fundingRate") or 0) * 100,
                "open_interest": float(ticker.get("openInterest") or 0),
                "orderbook_imbalance_pct": imbalance,
                "source_status": "ok",
            }
        except Exception as exc:
            logger.warning("Bybit public futures adapter failed for %s: %s", symbol, exc)
            return {"source_status": "error", "error": str(exc)}
