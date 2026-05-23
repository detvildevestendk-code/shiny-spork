from fastapi import APIRouter

from app.strategies.registry import build_default_registry

router = APIRouter(prefix="/strategies", tags=["strategies"])


@router.get("")
async def list_strategies() -> list[dict]:
    return [
        {"name": strategy.name, "timeframe": strategy.timeframe, "enabled": True}
        for strategy in build_default_registry().all()
    ]
