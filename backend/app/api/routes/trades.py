from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_api_key
from app.db.session import get_session
from app.trading.paper import PaperTradingStore

router = APIRouter(prefix="/trades", tags=["trades"], dependencies=[Depends(require_api_key)])


@router.get("")
async def list_trades(session: AsyncSession = Depends(get_session), limit: int = 100) -> dict:
    return await PaperTradingStore(session).trade_history(limit=limit)
