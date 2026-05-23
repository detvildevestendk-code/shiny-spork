from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.cache.redis import get_redis
from app.db.session import get_session

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/live")
async def liveness_check() -> dict[str, str]:
    return {"status": "ok"}


@router.get("")
@router.get("/ready")
async def readiness_check(
    session: AsyncSession = Depends(get_session),
    redis: Redis = Depends(get_redis),
) -> JSONResponse:
    checks: dict[str, str] = {}
    http_status = status.HTTP_200_OK

    try:
        await session.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception:
        checks["database"] = "error"
        http_status = status.HTTP_503_SERVICE_UNAVAILABLE

    try:
        await redis.ping()
        checks["redis"] = "ok"
        checks["worker_heartbeat"] = "ok" if await redis.get("worker:heartbeat") else "missing"
    except Exception:
        checks["redis"] = "error"
        http_status = status.HTTP_503_SERVICE_UNAVAILABLE
    finally:
        await redis.aclose()

    return JSONResponse(
        status_code=http_status,
        content={"status": "ok" if http_status == status.HTTP_200_OK else "degraded", "checks": checks},
    )
