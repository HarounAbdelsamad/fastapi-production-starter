import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

import app.events  # noqa: F401
from app.core.cache import close_redis
from app.core.config import get_settings
from app.core.errors import api_error
from app.core.exceptions import (
    http_exception_handler,
    unhandled_exception_handler,
    validation_exception_handler,
)
from app.core.logging import setup_logging
from app.core.middleware import RequestIDMiddleware, SecurityHeadersMiddleware
from app.core.rate_limit import get_limiter
from app.core.telemetry import setup_telemetry
from app.db.database import init_db
from app.internal import admin
from app.routers import (
    api_keys,
    audit,
    auth,
    features,
    files,
    gdpr,
    health,
    oauth,
    roles,
    saml,
    user,
    ws,
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    setup_logging(
        debug=settings.DEBUG, log_format=settings.LOG_FORMAT, pii_redact=settings.LOG_PII_REDACT
    )
    setup_telemetry(app, settings=settings)
    if settings.SENTRY_DSN:
        import sentry_sdk

        sentry_sdk.init(
            dsn=settings.SENTRY_DSN,
            traces_sample_rate=settings.SENTRY_TRACES_SAMPLE_RATE,
            environment=settings.APP_ENV,
        )
    logger.info("Starting %s (%s)", settings.APP_TITLE, settings.APP_ENV)
    await init_db()
    yield
    await close_redis()
    logger.info("Shutting down")


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title=settings.APP_TITLE,
        description=settings.APP_DESCRIPTION,
        version=settings.APP_VERSION,
        lifespan=lifespan,
        docs_url="/docs" if settings.is_development else None,
        redoc_url="/redoc" if settings.is_development else None,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=settings.CORS_ALLOW_METHODS,
        allow_headers=settings.CORS_ALLOW_HEADERS,
        max_age=settings.CORS_MAX_AGE,
    )
    app.add_middleware(RequestIDMiddleware)
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.TRUSTED_HOSTS)
    app.add_middleware(SlowAPIMiddleware)

    app.state.limiter = get_limiter()

    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
    app.add_exception_handler(
        RateLimitExceeded,
        lambda request, exc: api_error(
            status_code=429,
            code="TOO_MANY_REQUESTS",
            message="Rate limit exceeded",
            request=request,
        ),
    )

    app.include_router(health.router)
    app.include_router(auth.router, prefix="/api/v1/auth", tags=["Auth"])
    app.include_router(user.router, prefix="/api/v1/users", tags=["Users"])
    app.include_router(admin.router, prefix="/api/v1", tags=["Admin"])
    app.include_router(features.router, prefix="/api/v1", tags=["Features"])
    app.include_router(files.router, prefix="/api/v1/files", tags=["Files"])
    app.include_router(api_keys.router, prefix="/api/v1", tags=["API Keys"])
    app.include_router(roles.router, prefix="/api/v1", tags=["Roles & Permissions"])
    app.include_router(audit.router, prefix="/api/v1", tags=["Audit"])
    app.include_router(gdpr.router, prefix="/api/v1", tags=["GDPR"])
    if settings.WEBSOCKET_ENABLED:
        app.include_router(ws.router, prefix="/api/v1", tags=["WebSocket"])

    if settings.METRICS_ENABLED:
        from prometheus_fastapi_instrumentator import Instrumentator

        Instrumentator().instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)
    if settings.OAUTH_GOOGLE_CLIENT_ID or settings.OAUTH_GITHUB_CLIENT_ID:
        app.include_router(oauth.router, prefix="/api/v1/auth", tags=["OAuth"])
    app.include_router(saml.router, prefix="/api/v1/auth", tags=["SAML"])

    return app


app = create_app()
