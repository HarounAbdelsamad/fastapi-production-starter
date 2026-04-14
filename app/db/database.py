import asyncio
import logging
from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()

connect_args: dict = {}
if settings.is_sqlite:
    connect_args["check_same_thread"] = False

engine_kwargs: dict = {
    "echo": settings.DEBUG,
    "connect_args": connect_args,
}
if not settings.is_sqlite:
    engine_kwargs["pool_size"] = settings.DB_POOL_SIZE
    engine_kwargs["max_overflow"] = settings.DB_MAX_OVERFLOW

engine = create_async_engine(
    settings.DATABASE_URL,
    **engine_kwargs,
)

SessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


_tables_lock = asyncio.Lock()
_tables_created = False


async def init_db() -> None:
    """Create all ORM tables if they don't exist yet (idempotent)."""
    global _tables_created
    if _tables_created or not settings.AUTO_CREATE_TABLES:
        return
    async with _tables_lock:
        if _tables_created:
            return
        from app.models.revoked_token import RevokedToken  # noqa: F401
        from app.models.user import User  # noqa: F401 — register models

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        _tables_created = True
        logger.info("Database tables ensured")


async def get_session() -> AsyncIterator[AsyncSession]:
    await init_db()
    async with SessionLocal() as session:
        yield session
