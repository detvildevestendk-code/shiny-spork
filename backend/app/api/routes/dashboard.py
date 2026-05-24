from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_api_key
from app.api.paper_deps import refresh_paper_store
from app.db.session import get_session
from app.intelligence.service import MarketIntelligenceService
from app.trading.paper import PaperTradingStore

router = APIRouter(prefix="/dashboard", tags=["dashboard"], dependencies=[Depends(require_api_key)])


@router.get("/summary")
async def dashboard_summary(session: AsyncSession = Depends(get_session)) -> dict:
    store = PaperTradingStore(session)
    refresh = await refresh_paper_store(store)
    summary = await store.dashboard_summary()
    summary["paper_refresh"] = refresh
    intelligence = await MarketIntelligenceService().snapshot()
    summary.update(intelligence.model_dump(mode="json"))
    return summary


@router.get("/trades")
async def trade_history(session: AsyncSession = Depends(get_session)) -> dict:
    store = PaperTradingStore(session)
    await refresh_paper_store(store)
    return await store.trade_history()
