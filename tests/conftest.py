import os
from pathlib import Path
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import get_settings


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest.fixture()
async def client():
    """Async test client that runs the full app over ASGI."""
    db_path = Path(f"test-{uuid4().hex}.db")
    os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///./{db_path.name}"
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
    from app.main import create_app

    app = create_app()
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac
    try:
        if db_path.exists():
            db_path.unlink()
    except PermissionError:
        pass
