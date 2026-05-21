import os
from pathlib import Path
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import get_settings


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


def _resolve_test_db() -> tuple[str, Path | None]:
    """Return (database_url, sqlite_path_or_None).

    When CI_DATABASE_URL is set (Postgres/MySQL CI matrix), use it directly.
    Otherwise create a unique ephemeral SQLite file so every test is isolated.
    """
    ci_url = os.environ.get("CI_DATABASE_URL", "")
    if ci_url:
        return ci_url, None
    db_path = Path(f"test-{uuid4().hex}.db")
    return f"sqlite+aiosqlite:///./{db_path.name}", db_path


@pytest.fixture()
async def client():
    """Async test client backed by the full ASGI app.

    - Local / SQLite: each test gets a fresh, isolated database file.
    - CI matrix (Postgres/MySQL): tests share the service container DB;
      each test creates data with unique UUIDs so there is no cross-test
      interference.
    """
    db_url, db_path = _resolve_test_db()

    os.environ["DATABASE_URL"] = db_url
    os.environ["APP_ENV"] = "testing"
    os.environ["DEBUG"] = "false"
    os.environ["AUTO_CREATE_TABLES"] = "true"
    os.environ["TOKEN_REVOCATION_ENABLED"] = "true"
    os.environ["RATE_LIMIT_ENABLED"] = "false"
    os.environ["CACHE_ENABLED"] = "false"
    os.environ["CELERY_ENABLED"] = "false"
    os.environ["METRICS_ENABLED"] = "false"
    os.environ["WEBSOCKET_ENABLED"] = "false"
    os.environ["FEATURE_FLAGS_ENABLED"] = "false"
    os.environ["API_KEYS"] = "[]"

    get_settings.cache_clear()

    # Reset engine cache so the new DATABASE_URL takes effect.
    # Always reset — even for Postgres/MySQL — so each test gets a fresh
    # connection pool tied to the current event loop (avoids "Future attached
    # to a different loop" errors with asyncpg/aiomysql).
    from app.db import database as _db

    _db.engine = None
    _db.SessionLocal = None
    _db._tables_created = False
    _db._current_db_url = None

    from app.main import create_app

    app = create_app()
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac

    # Cleanup: remove the ephemeral SQLite file.
    if db_path is not None:
        try:
            if db_path.exists():
                db_path.unlink()
        except PermissionError:
            pass
