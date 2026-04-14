from uuid import uuid4

import pytest


def make_user_payload() -> dict[str, str]:
    uid = uuid4().hex[:8]
    return {
        "user_id": f"u-{uid}",
        "username": f"user-{uid}",
        "password": "s3cret-password",
        "email": f"{uid}@example.com",
        "phone_number": "1234567890",
    }


async def auth_headers(client, payload: dict[str, str]) -> dict[str, str]:
    login = await client.post(
        "/api/auth/login",
        data={"username": payload["username"], "password": payload["password"]},
    )
    token = login.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_create_user(client):
    payload = make_user_payload()
    resp = await client.post("/api/users/", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["user_id"] == payload["user_id"]
    assert data["username"] == payload["username"]
    assert "password" not in data
    assert "password_hash" not in data


@pytest.mark.asyncio
async def test_create_duplicate_user(client):
    payload = make_user_payload()
    await client.post("/api/users/", json=payload)
    resp = await client.post("/api/users/", json=payload)
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_get_user(client):
    payload = make_user_payload()
    await client.post("/api/users/", json=payload)
    headers = await auth_headers(client, payload)
    resp = await client.get(f"/api/users/{payload['user_id']}", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["email"] == payload["email"]


@pytest.mark.asyncio
async def test_get_user_not_found(client):
    payload = make_user_payload()
    await client.post("/api/users/", json=payload)
    headers = await auth_headers(client, payload)
    resp = await client.get("/api/users/nonexistent", headers=headers)
    assert resp.status_code in (401, 404)


@pytest.mark.asyncio
async def test_list_users(client):
    payload = make_user_payload()
    await client.post("/api/users/", json=payload)
    headers = await auth_headers(client, payload)
    resp = await client.get("/api/users/?skip=0&limit=10", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "total" in data
    assert isinstance(data["items"], list)


@pytest.mark.asyncio
async def test_update_user(client):
    payload = make_user_payload()
    await client.post("/api/users/", json=payload)
    headers = await auth_headers(client, payload)
    resp = await client.patch(
        f"/api/users/{payload['user_id']}",
        json={"username": "updated"},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["username"] == "updated"


@pytest.mark.asyncio
async def test_delete_user(client):
    payload = make_user_payload()
    await client.post("/api/users/", json=payload)
    headers = await auth_headers(client, payload)
    resp = await client.delete(f"/api/users/{payload['user_id']}", headers=headers)
    assert resp.status_code == 204

    resp = await client.get(f"/api/users/{payload['user_id']}", headers=headers)
    assert resp.status_code in (401, 404)
