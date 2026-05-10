"""Tests for DB-backed API key issuance, listing, revocation, and rotation."""

from uuid import uuid4

# ── helpers ────────────────────────────────────────────────────────────────


async def _register_and_login(client, suffix: str = "") -> tuple[str, str]:
    """Create a user and return (user_id, JWT access token)."""
    uid = uuid4().hex
    username = f"apikey_user_{uid}{suffix}"
    email = f"{username}@example.com"
    resp = await client.post(
        "/api/v1/users/",
        json={
            "user_id": uid,
            "username": username,
            "password": "Pass1234!",
            "email": email,
            "phone_number": None,
            "role": "user",
        },
    )
    assert resp.status_code == 201, resp.text

    token_resp = await client.post(
        "/api/v1/auth/login",
        data={"username": username, "password": "Pass1234!"},
    )
    assert token_resp.status_code == 200
    return uid, token_resp.json()["access_token"]


# ── issue ──────────────────────────────────────────────────────────────────


class TestIssueApiKey:
    async def test_create_returns_201(self, client):
        _, token = await _register_and_login(client)
        resp = await client.post(
            "/api/v1/api-keys",
            json={"name": "my-key"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 201

    async def test_create_returns_raw_key(self, client):
        _, token = await _register_and_login(client)
        resp = await client.post(
            "/api/v1/api-keys",
            json={"name": "test-key"},
            headers={"Authorization": f"Bearer {token}"},
        )
        data = resp.json()
        assert "key" in data
        assert data["key"].startswith("fpsk_")

    async def test_create_with_scopes(self, client):
        _, token = await _register_and_login(client)
        resp = await client.post(
            "/api/v1/api-keys",
            json={"name": "scoped", "scopes": ["users:read", "api-keys:read"]},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 201
        assert set(resp.json()["scopes"]) == {"users:read", "api-keys:read"}

    async def test_create_requires_auth(self, client):
        resp = await client.post("/api/v1/api-keys", json={"name": "x"})
        assert resp.status_code == 401


# ── list ───────────────────────────────────────────────────────────────────


class TestListApiKeys:
    async def test_list_returns_created_key(self, client):
        _, token = await _register_and_login(client)
        await client.post(
            "/api/v1/api-keys",
            json={"name": "list-test"},
            headers={"Authorization": f"Bearer {token}"},
        )
        resp = await client.get("/api/v1/api-keys", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        names = [k["name"] for k in resp.json()]
        assert "list-test" in names

    async def test_list_does_not_expose_raw_key(self, client):
        _, token = await _register_and_login(client)
        await client.post(
            "/api/v1/api-keys",
            json={"name": "hidden"},
            headers={"Authorization": f"Bearer {token}"},
        )
        resp = await client.get("/api/v1/api-keys", headers={"Authorization": f"Bearer {token}"})
        for k in resp.json():
            assert "key" not in k

    async def test_list_isolated_per_user(self, client):
        _, token_a = await _register_and_login(client, suffix="a")
        _, token_b = await _register_and_login(client, suffix="b")
        await client.post(
            "/api/v1/api-keys",
            json={"name": "user-a-key"},
            headers={"Authorization": f"Bearer {token_a}"},
        )
        resp = await client.get("/api/v1/api-keys", headers={"Authorization": f"Bearer {token_b}"})
        names = [k["name"] for k in resp.json()]
        assert "user-a-key" not in names


# ── revoke ─────────────────────────────────────────────────────────────────


class TestRevokeApiKey:
    async def test_revoke_returns_204(self, client):
        _, token = await _register_and_login(client)
        create_resp = await client.post(
            "/api/v1/api-keys",
            json={"name": "to-revoke"},
            headers={"Authorization": f"Bearer {token}"},
        )
        key_id = create_resp.json()["key_id"]
        resp = await client.delete(
            f"/api/v1/api-keys/{key_id}", headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 204

    async def test_revoked_key_cannot_authenticate(self, client):
        _, token = await _register_and_login(client)
        create_resp = await client.post(
            "/api/v1/api-keys",
            json={"name": "revoke-auth-test"},
            headers={"Authorization": f"Bearer {token}"},
        )
        data = create_resp.json()
        key_id, raw_key = data["key_id"], data["key"]

        await client.delete(
            f"/api/v1/api-keys/{key_id}", headers={"Authorization": f"Bearer {token}"}
        )

        resp = await client.get("/api/v1/api-keys", headers={"X-API-Key": raw_key})
        assert resp.status_code == 401

    async def test_revoke_wrong_owner_returns_404(self, client):
        _, token_a = await _register_and_login(client, suffix="own_a")
        _, token_b = await _register_and_login(client, suffix="own_b")
        create_resp = await client.post(
            "/api/v1/api-keys",
            json={"name": "belongs-to-a"},
            headers={"Authorization": f"Bearer {token_a}"},
        )
        key_id = create_resp.json()["key_id"]
        resp = await client.delete(
            f"/api/v1/api-keys/{key_id}", headers={"Authorization": f"Bearer {token_b}"}
        )
        assert resp.status_code == 404


# ── authenticate ───────────────────────────────────────────────────────────


class TestAuthenticateWithApiKey:
    async def test_api_key_grants_access(self, client):
        _, token = await _register_and_login(client)
        create_resp = await client.post(
            "/api/v1/api-keys",
            json={"name": "auth-test"},
            headers={"Authorization": f"Bearer {token}"},
        )
        raw_key = create_resp.json()["key"]

        resp = await client.get("/api/v1/api-keys", headers={"X-API-Key": raw_key})
        assert resp.status_code == 200

    async def test_invalid_api_key_returns_401(self, client):
        resp = await client.get("/api/v1/api-keys", headers={"X-API-Key": "fpsk_invalid"})
        assert resp.status_code == 401


# ── rotate ─────────────────────────────────────────────────────────────────


class TestRotateApiKey:
    async def test_rotate_returns_new_key(self, client):
        _, token = await _register_and_login(client)
        create_resp = await client.post(
            "/api/v1/api-keys",
            json={"name": "rotate-me"},
            headers={"Authorization": f"Bearer {token}"},
        )
        data = create_resp.json()
        key_id, old_raw = data["key_id"], data["key"]

        rotate_resp = await client.post(
            f"/api/v1/api-keys/{key_id}/rotate",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert rotate_resp.status_code == 200
        new_key = rotate_resp.json()["key"]
        assert new_key != old_raw
        assert new_key.startswith("fpsk_")

    async def test_old_key_rejected_after_rotate(self, client):
        _, token = await _register_and_login(client)
        create_resp = await client.post(
            "/api/v1/api-keys",
            json={"name": "rotate-auth"},
            headers={"Authorization": f"Bearer {token}"},
        )
        data = create_resp.json()
        key_id, old_raw = data["key_id"], data["key"]

        await client.post(
            f"/api/v1/api-keys/{key_id}/rotate",
            headers={"Authorization": f"Bearer {token}"},
        )

        resp = await client.get("/api/v1/api-keys", headers={"X-API-Key": old_raw})
        assert resp.status_code == 401
