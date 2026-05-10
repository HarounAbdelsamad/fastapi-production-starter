import asyncio
import logging
from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.config import get_settings

logger = logging.getLogger(__name__)

engine: AsyncEngine | None = None
read_engine: AsyncEngine | None = None
SessionLocal: async_sessionmaker[AsyncSession] | None = None
ReadSessionLocal: async_sessionmaker[AsyncSession] | None = None
_current_db_url: str | None = None


class Base(DeclarativeBase):
    pass


_tables_lock = asyncio.Lock()
_tables_created = False


def _build_engine(db_url: str) -> AsyncEngine:
    settings = get_settings()
    connect_args: dict = {}
    if db_url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
    engine_kwargs: dict = {
        "echo": settings.DEBUG,
        "connect_args": connect_args,
    }
    if not db_url.startswith("sqlite"):
        engine_kwargs["pool_size"] = settings.DB_POOL_SIZE
        engine_kwargs["max_overflow"] = settings.DB_MAX_OVERFLOW
    return create_async_engine(db_url, **engine_kwargs)


def _ensure_session_factories() -> None:
    global engine, read_engine, SessionLocal, ReadSessionLocal, _current_db_url, _tables_created  # noqa: PLW0603,E501
    settings = get_settings()
    if SessionLocal is not None and _current_db_url == settings.DATABASE_URL:
        return
    engine = _build_engine(settings.DATABASE_URL)
    read_engine = (
        _build_engine(settings.DB_READ_REPLICA_URL) if settings.DB_READ_REPLICA_URL else engine
    )
    SessionLocal = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    ReadSessionLocal = async_sessionmaker(
        bind=read_engine, class_=AsyncSession, expire_on_commit=False
    )
    _current_db_url = settings.DATABASE_URL
    _tables_created = False


async def init_db() -> None:
    """Create all ORM tables if they don't exist yet (idempotent)."""
    _ensure_session_factories()
    assert engine is not None
    global _tables_created
    settings = get_settings()
    if _tables_created or not settings.AUTO_CREATE_TABLES:
        return
    async with _tables_lock:
        if _tables_created:
            return
        from app.models.api_key import ApiKey  # noqa: F401
        from app.models.audit_log import AuditLog  # noqa: F401
        from app.models.feature_flag import FeatureFlag  # noqa: F401
        from app.models.oauth_account import OAuthAccount  # noqa: F401
        from app.models.revoked_token import RevokedToken  # noqa: F401
        from app.models.role import Permission, Role, RolePermission, UserRole  # noqa: F401
        from app.models.user import User  # noqa: F401 — register models

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        _tables_created = True
        logger.info("Database tables ensured")


async def get_session() -> AsyncIterator[AsyncSession]:
    await init_db()
    assert SessionLocal is not None
    async with SessionLocal() as session:
        yield session


async def get_read_session() -> AsyncIterator[AsyncSession]:
    await init_db()
    assert ReadSessionLocal is not None
    async with ReadSessionLocal() as session:
        yield session
