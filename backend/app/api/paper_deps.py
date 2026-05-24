from app.exchanges.factory import get_exchange_client
from app.trading.paper import PaperTradingStore


async def refresh_paper_store(store: PaperTradingStore) -> dict:
    exchange = get_exchange_client()
    try:
        return await store.refresh_market_prices(exchange)
    finally:
        await exchange.close()
