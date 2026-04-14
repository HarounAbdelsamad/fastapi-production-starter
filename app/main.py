import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.core.cache import close_redis
from app.core.config import get_settings
from app.core.exceptions import unhandled_exception_handler
from app.core.logging import setup_logging
from app.db.database import init_db
from app.internal import admin
from app.routers import auth, health, user

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    setup_logging(debug=settings.DEBUG)
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
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.TRUSTED_HOSTS)

    app.add_exception_handler(Exception, unhandled_exception_handler)

    app.include_router(health.router)
    app.include_router(auth.router, prefix="/api/auth", tags=["Auth"])
    app.include_router(user.router, prefix="/api/users", tags=["Users"])
    app.include_router(admin.router, prefix="/api", tags=["Admin"])

    return app


app = create_app()
