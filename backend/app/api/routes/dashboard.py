from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_api_key
from app.db.session import get_session
from app.trading.paper import PaperTradingStore

router = APIRouter(prefix="/dashboard", tags=["dashboard"], dependencies=[Depends(require_api_key)])


@router.get("/summary")
async def dashboard_summary(session: AsyncSession = Depends(get_session)) -> dict:
    return await PaperTradingStore(session).dashboard_summary()


@router.get("/trades")
async def trade_history(session: AsyncSession = Depends(get_session)) -> dict:
    return await PaperTradingStore(session).trade_history()
