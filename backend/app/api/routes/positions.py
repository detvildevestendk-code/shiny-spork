from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_api_key
from app.db.session import get_session
from app.trading.paper import PaperTradingStore

router = APIRouter(prefix="/positions", tags=["positions"], dependencies=[Depends(require_api_key)])


@router.get("")
async def list_positions(session: AsyncSession = Depends(get_session)) -> dict:
    return await PaperTradingStore(session).positions()
