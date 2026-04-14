from uuid import uuid4

import pytest


def make_payload(role: str = "admin") -> dict[str, str]:
    uid = uuid4().hex[:8]
    return {
        "user_id": f"u-{uid}",
        "username": f"user-{uid}",
        "password": "s3cret-password",
        "email": f"{uid}@example.com",
        "phone_number": "111",
        "role": role,
    }


@pytest.mark.asyncio
async def test_admin_can_read_audit_logs(client):
    payload = make_payload("admin")
    await client.post("/api/v1/users/", json=payload)
    login = await client.post(
        "/api/v1/auth/login",
        data={"username": payload["username"], "password": payload["password"]},
    )
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    resp = await client.get("/api/v1/admin/audit-logs", headers=headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
