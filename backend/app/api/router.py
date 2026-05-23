from fastapi import APIRouter

from app.api.routes import dashboard, health, strategies, trading

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health.router)
api_router.include_router(trading.router)
api_router.include_router(dashboard.router)
api_router.include_router(strategies.router)
