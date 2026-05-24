from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_api_key
from app.api.paper_deps import refresh_paper_store
from app.db.session import get_session
from app.intelligence.service import MarketIntelligenceService
from app.trading.paper import PaperTradingStore
from app.trading.signal_decisions import latest_signal_decision

router = APIRouter(prefix="/dashboard", tags=["dashboard"], dependencies=[Depends(require_api_key)])


@router.get("/summary")
async def dashboard_summary(session: AsyncSession = Depends(get_session)) -> dict:
    store = PaperTradingStore(session)
    refresh = await refresh_paper_store(store)
    summary = await store.dashboard_summary()
    summary["paper_refresh"] = refresh
    latest_decision = await latest_signal_decision(session)
    if latest_decision:
        summary["latest_agent_action"] = latest_decision.decision
        summary["latest_signal_reason"] = latest_decision.reason
        summary["latest_signal"] = {
            "symbol": latest_decision.symbol,
            "strategy_name": latest_decision.strategy_name,
            "action": latest_decision.action,
            "confidence": float(latest_decision.confidence),
            "decision": latest_decision.decision,
            "reason": latest_decision.reason,
            "created_at": latest_decision.created_at.isoformat() if latest_decision.created_at else None,
        }
    else:
        summary["latest_agent_action"] = "idle"
        summary["latest_signal_reason"] = "No worker signal decisions recorded yet"
    intelligence = await MarketIntelligenceService().snapshot()
    summary.update(intelligence.model_dump(mode="json"))
    return summary


@router.get("/trades")
async def trade_history(session: AsyncSession = Depends(get_session)) -> dict:
    store = PaperTradingStore(session)
    await refresh_paper_store(store)
    return await store.trade_history()
