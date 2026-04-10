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

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    connect_args=connect_args,
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
    if _tables_created:
        return
    async with _tables_lock:
        if _tables_created:
            return
        from app.models.user import User  # noqa: F401 — register models

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        _tables_created = True
        logger.info("Database tables ensured")


async def get_session() -> AsyncIterator[AsyncSession]:
    await init_db()
    async with SessionLocal() as session:
        yield session
