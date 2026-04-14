import pytest


@pytest.mark.asyncio
async def test_request_id_is_present(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert "x-request-id" in {k.lower(): v for k, v in resp.headers.items()}


@pytest.mark.asyncio
async def test_request_id_echoed_when_provided(client):
    resp = await client.get("/health", headers={"X-Request-ID": "abc123"})
    assert resp.status_code == 200
    assert resp.headers["X-Request-ID"] == "abc123"


@pytest.mark.asyncio
async def test_security_headers_exist(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.headers.get("X-Content-Type-Options") == "nosniff"
