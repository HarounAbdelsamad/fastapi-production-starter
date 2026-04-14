import os

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import get_settings
from app.main import create_app


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest.fixture()
async def client():
    """Async test client that runs the full app over ASGI."""
    os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./test.db"
    os.environ["APP_ENV"] = "testing"
    os.environ["DEBUG"] = "false"
    os.environ["AUTO_CREATE_TABLES"] = "true"
    os.environ["TOKEN_REVOCATION_ENABLED"] = "true"
    get_settings.cache_clear()
    app = create_app()
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac
