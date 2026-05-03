import pytest


@pytest.mark.asyncio
async def test_health_check(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_liveness_check(client):
    resp = await client.get("/health/live")
    assert resp.status_code == 200
    assert resp.json() == {"status": "alive"}


@pytest.mark.asyncio
async def test_readiness_check(client):
    resp = await client.get("/health/ready")
    assert resp.status_code == 200
    data = resp.json()
    assert data["checks"]["database"] == "ok"


@pytest.mark.asyncio
async def test_dependencies_check_structure(client):
    resp = await client.get("/health/dependencies")
    assert resp.status_code == 200
    data = resp.json()

    assert "status" in data
    assert data["status"] in ("ok", "degraded")
    assert "dependencies" in data

    deps = data["dependencies"]
    assert "database" in deps
    assert "redis" in deps
    assert "celery" in deps


@pytest.mark.asyncio
async def test_dependencies_database_ok(client):
    resp = await client.get("/health/dependencies")
    data = resp.json()
    assert data["dependencies"]["database"]["status"] == "ok"
    assert "latency_ms" in data["dependencies"]["database"]
    assert isinstance(data["dependencies"]["database"]["latency_ms"], float)


@pytest.mark.asyncio
async def test_dependencies_redis_disabled_by_default(client):
    """Redis is disabled in the test client fixture (CACHE_ENABLED=false)."""
    resp = await client.get("/health/dependencies")
    data = resp.json()
    assert data["dependencies"]["redis"]["status"] == "disabled"


@pytest.mark.asyncio
async def test_dependencies_celery_disabled_by_default(client):
    """Celery is disabled in the test client fixture (CELERY_ENABLED=false)."""
    resp = await client.get("/health/dependencies")
    data = resp.json()
    assert data["dependencies"]["celery"]["status"] == "disabled"


@pytest.mark.asyncio
async def test_dependencies_overall_ok_when_db_reachable(client):
    resp = await client.get("/health/dependencies")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
