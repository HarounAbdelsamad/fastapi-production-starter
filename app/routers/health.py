from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import get_redis
from app.core.config import get_settings
from app.db.database import get_session

router = APIRouter(tags=["Health"])


@router.get("/health", summary="Health check")
async def health_check() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/health/live", summary="Liveness check")
async def liveness_check() -> dict[str, str]:
    return {"status": "alive"}


@router.get("/health/ready", summary="Readiness check")
async def readiness_check(
    db: AsyncSession = Depends(get_session),
) -> JSONResponse:
    settings = get_settings()
    checks: dict[str, str] = {"database": "ok", "redis": "disabled", "celery": "disabled"}
    http_status = status.HTTP_200_OK

    try:
        await db.execute(text("SELECT 1"))
    except Exception:
        checks["database"] = "unavailable"
        http_status = status.HTTP_503_SERVICE_UNAVAILABLE

    if settings.CACHE_ENABLED:
        redis = await get_redis()
        try:
            if redis is None:
                checks["redis"] = "unavailable"
                http_status = status.HTTP_503_SERVICE_UNAVAILABLE
            else:
                await redis.ping()
                checks["redis"] = "ok"
        except Exception:
            checks["redis"] = "unavailable"
            http_status = status.HTTP_503_SERVICE_UNAVAILABLE

    if settings.CELERY_ENABLED:
        checks["celery"] = "ok"

    return JSONResponse(status_code=http_status, content={"status": "ready", "checks": checks})
