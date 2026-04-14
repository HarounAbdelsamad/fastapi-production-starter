from uuid import uuid4

import pytest


def make_user_payload(role: str = "user") -> dict[str, str]:
    uid = uuid4().hex[:8]
    return {
        "user_id": f"u-{uid}",
        "username": f"user-{uid}",
        "password": "s3cret-password",
        "email": f"{uid}@example.com",
        "phone_number": "1234567890",
        "role": role,
    }


@pytest.mark.asyncio
async def test_login_and_refresh(client):
    payload = make_user_payload()
    await client.post("/api/v1/users/", json=payload)

    login_resp = await client.post(
        "/api/v1/auth/login",
        data={"username": payload["username"], "password": payload["password"]},
    )
    assert login_resp.status_code == 200
    tokens = login_resp.json()
    assert "access_token" in tokens
    assert "refresh_token" in tokens

    refresh_resp = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": tokens["refresh_token"]},
    )
    assert refresh_resp.status_code == 200
    refreshed = refresh_resp.json()
    assert refreshed["access_token"] != tokens["access_token"]


@pytest.mark.asyncio
async def test_logout_revokes_access(client):
    payload = make_user_payload()
    await client.post("/api/v1/users/", json=payload)

    login_resp = await client.post(
        "/api/v1/auth/login",
        data={"username": payload["username"], "password": payload["password"]},
    )
    tokens = login_resp.json()
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    logout_resp = await client.post("/api/v1/auth/logout", headers=headers)
    assert logout_resp.status_code == 204

    protected_resp = await client.get("/api/v1/users/", headers=headers)
    assert protected_resp.status_code == 401


@pytest.mark.asyncio
async def test_password_reset_flow(client):
    payload = make_user_payload()
    await client.post("/api/v1/users/", json=payload)

    request_resp = await client.post(
        "/api/v1/auth/password-reset/request",
        json={"email": payload["email"]},
    )
    assert request_resp.status_code == 202
    token = request_resp.json()["reset_token"]

    confirm_resp = await client.post(
        "/api/v1/auth/password-reset/confirm",
        json={"token": token, "new_password": "new-password-123"},
    )
    assert confirm_resp.status_code == 200


@pytest.mark.asyncio
async def test_rbac_admin_guard(client):
    user_payload = make_user_payload(role="user")
    await client.post("/api/v1/users/", json=user_payload)
    user_login = await client.post(
        "/api/v1/auth/login",
        data={"username": user_payload["username"], "password": user_payload["password"]},
    )
    user_headers = {"Authorization": f"Bearer {user_login.json()['access_token']}"}

    forbidden = await client.get("/api/v1/admin/dashboard", headers=user_headers)
    assert forbidden.status_code == 403

    admin_payload = make_user_payload(role="admin")
    await client.post("/api/v1/users/", json=admin_payload)
    admin_login = await client.post(
        "/api/v1/auth/login",
        data={"username": admin_payload["username"], "password": admin_payload["password"]},
    )
    admin_headers = {"Authorization": f"Bearer {admin_login.json()['access_token']}"}

    allowed = await client.get("/api/v1/admin/dashboard", headers=admin_headers)
    assert allowed.status_code == 200


@pytest.mark.asyncio
async def test_login_lockout(client):
    payload = make_user_payload()
    await client.post("/api/v1/users/", json=payload)
    status_codes = []
    for _ in range(7):
        resp = await client.post(
            "/api/v1/auth/login",
            data={"username": payload["username"], "password": "wrong-password"},
        )
        status_codes.append(resp.status_code)
    assert 429 in status_codes
