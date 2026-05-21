import time

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
    """Process is running.  Returns 200 as long as the event loop is alive."""
    return {"status": "alive"}


@router.get("/health/ready", summary="Readiness check")
async def readiness_check(
    db: AsyncSession = Depends(get_session),
) -> JSONResponse:
    """Process can serve traffic.  Returns 503 if any required dependency is unavailable."""
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
                await redis.ping()  # type: ignore[misc]
                checks["redis"] = "ok"
        except Exception:
            checks["redis"] = "unavailable"
            http_status = status.HTTP_503_SERVICE_UNAVAILABLE

    if settings.CELERY_ENABLED:
        checks["celery"] = "ok"

    return JSONResponse(status_code=http_status, content={"status": "ready", "checks": checks})


@router.get("/health/dependencies", summary="Dependency health with latency")
async def dependencies_check(
    db: AsyncSession = Depends(get_session),
) -> JSONResponse:
    """Per-dependency health status with measured latency.

    Returns 200 when all enabled dependencies are reachable.
    Returns 503 when any enabled dependency is unavailable.

    Response shape::

        {
          "status": "ok" | "degraded",
          "dependencies": {
            "database": {"status": "ok", "latency_ms": 3.2},
            "redis":    {"status": "disabled"},
            "celery":   {"status": "ok"}
          }
        }
    """
    settings = get_settings()
    dependencies: dict[str, dict] = {}
    overall_ok = True

    # Database
    try:
        t0 = time.perf_counter()
        await db.execute(text("SELECT 1"))
        latency_ms = round((time.perf_counter() - t0) * 1000, 2)
        dependencies["database"] = {"status": "ok", "latency_ms": latency_ms}
    except Exception as exc:
        dependencies["database"] = {"status": "unavailable", "error": str(exc)}
        overall_ok = False

    # Redis
    if settings.CACHE_ENABLED:
        redis = await get_redis()
        if redis is None:
            dependencies["redis"] = {"status": "unavailable", "error": "client not initialised"}
            overall_ok = False
        else:
            try:
                t0 = time.perf_counter()
                await redis.ping()  # type: ignore[misc]
                latency_ms = round((time.perf_counter() - t0) * 1000, 2)
                dependencies["redis"] = {"status": "ok", "latency_ms": latency_ms}
            except Exception as exc:
                dependencies["redis"] = {"status": "unavailable", "error": str(exc)}
                overall_ok = False
    else:
        dependencies["redis"] = {"status": "disabled"}

    # Celery — basic presence check (no broker ping; would require a worker connection)
    if settings.CELERY_ENABLED:
        dependencies["celery"] = {"status": "ok"}
    else:
        dependencies["celery"] = {"status": "disabled"}

    http_status = status.HTTP_200_OK if overall_ok else status.HTTP_503_SERVICE_UNAVAILABLE
    return JSONResponse(
        status_code=http_status,
        content={
            "status": "ok" if overall_ok else "degraded",
            "dependencies": dependencies,
        },
    )
