import pytest

USER_PAYLOAD = {
    "user_id": "u1",
    "username": "testuser",
    "password": "s3cret!",
    "email": "test@example.com",
    "phone_number": "1234567890",
}


@pytest.mark.asyncio
async def test_create_user(client):
    resp = await client.post("/api/users/", json=USER_PAYLOAD)
    assert resp.status_code == 201
    data = resp.json()
    assert data["user_id"] == "u1"
    assert data["username"] == "testuser"
    assert "password" not in data
    assert "password_hash" not in data


@pytest.mark.asyncio
async def test_create_duplicate_user(client):
    await client.post("/api/users/", json=USER_PAYLOAD)
    resp = await client.post("/api/users/", json=USER_PAYLOAD)
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_get_user(client):
    await client.post("/api/users/", json=USER_PAYLOAD)
    resp = await client.get("/api/users/u1")
    assert resp.status_code == 200
    assert resp.json()["email"] == "test@example.com"


@pytest.mark.asyncio
async def test_get_user_not_found(client):
    resp = await client.get("/api/users/nonexistent")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_list_users(client):
    await client.post("/api/users/", json=USER_PAYLOAD)
    resp = await client.get("/api/users/")
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


@pytest.mark.asyncio
async def test_update_user(client):
    await client.post("/api/users/", json=USER_PAYLOAD)
    resp = await client.patch("/api/users/u1", json={"username": "updated"})
    assert resp.status_code == 200
    assert resp.json()["username"] == "updated"


@pytest.mark.asyncio
async def test_delete_user(client):
    await client.post("/api/users/", json=USER_PAYLOAD)
    resp = await client.delete("/api/users/u1")
    assert resp.status_code == 204

    resp = await client.get("/api/users/u1")
    assert resp.status_code == 404
