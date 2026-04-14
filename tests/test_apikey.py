import os
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import get_settings


@pytest.mark.asyncio
async def test_valid_api_key_accesses_protected_route():
    os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///./test-apikey-{uuid4().hex}.db"
    os.environ["AUTO_CREATE_TABLES"] = "true"
    os.environ["API_KEYS"] = '["test-key-123"]'
    get_settings.cache_clear()
    from app.main import create_app

    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v1/users/", headers={"X-API-Key": "test-key-123"})
        assert resp.status_code in (200, 422)


@pytest.mark.asyncio
async def test_invalid_api_key_is_rejected(client):
    resp = await client.get("/api/v1/users/", headers={"X-API-Key": "invalid"})
    assert resp.status_code == 401
