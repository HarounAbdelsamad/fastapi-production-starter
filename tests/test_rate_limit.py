import os

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import get_settings


@pytest.mark.asyncio
async def test_rate_limit_on_health_endpoint():
    os.environ["RATE_LIMIT_ENABLED"] = "true"
    os.environ["RATE_LIMIT_DEFAULT"] = "3/minute"
    get_settings.cache_clear()
    from app.main import create_app

    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        codes = []
        for _ in range(4):
            response = await client.get("/health")
            codes.append(response.status_code)
        assert codes[-1] == 429
