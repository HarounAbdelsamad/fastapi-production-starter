from uuid import uuid4

import pytest


@pytest.mark.asyncio
async def test_local_file_upload_and_delete(client):
    uid = uuid4().hex[:8]
    payload = {
        "user_id": f"u-{uid}",
        "username": f"user-{uid}",
        "password": "s3cret-password",
        "email": f"{uid}@example.com",
        "phone_number": "123",
    }
    await client.post("/api/v1/users/", json=payload)
    login = await client.post(
        "/api/v1/auth/login",
        data={"username": payload["username"], "password": payload["password"]},
    )
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    files = {"file": ("sample.txt", b"hello", "text/plain")}
    upload = await client.post("/api/v1/files/upload", files=files, headers=headers)
    assert upload.status_code == 200
    uploaded_path = upload.json()["path"]
    delete = await client.delete(f"/api/v1/files/{uploaded_path}", headers=headers)
    assert delete.status_code == 200
