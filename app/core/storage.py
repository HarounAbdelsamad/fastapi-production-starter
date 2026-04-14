import asyncio
from pathlib import Path
from typing import Protocol

import boto3
from fastapi import UploadFile

from app.core.config import get_settings


class StorageBackend(Protocol):
    async def upload(self, file: UploadFile, path: str) -> str: ...
    async def delete(self, path: str) -> None: ...
    async def get_url(self, path: str) -> str: ...


class LocalStorage:
    def __init__(self) -> None:
        self.base = Path(get_settings().STORAGE_LOCAL_PATH)
        self.base.mkdir(parents=True, exist_ok=True)

    async def upload(self, file: UploadFile, path: str) -> str:
        destination = self.base / path
        destination.parent.mkdir(parents=True, exist_ok=True)
        content = await file.read()
        await asyncio.to_thread(destination.write_bytes, content)
        return await self.get_url(path)

    async def delete(self, path: str) -> None:
        target = self.base / path
        if target.exists():
            await asyncio.to_thread(target.unlink)

    async def get_url(self, path: str) -> str:
        return f"/uploads/{path}"


class S3Storage:
    def __init__(self) -> None:
        settings = get_settings()
        self.bucket = settings.S3_BUCKET_NAME
        self.client = boto3.client(
            "s3",
            region_name=settings.S3_REGION or None,
            aws_access_key_id=settings.S3_ACCESS_KEY or None,
            aws_secret_access_key=settings.S3_SECRET_KEY or None,
            endpoint_url=settings.S3_ENDPOINT_URL or None,
        )

    async def upload(self, file: UploadFile, path: str) -> str:
        content = await file.read()
        await asyncio.to_thread(self.client.put_object, Bucket=self.bucket, Key=path, Body=content)
        return await self.get_url(path)

    async def delete(self, path: str) -> None:
        await asyncio.to_thread(self.client.delete_object, Bucket=self.bucket, Key=path)

    async def get_url(self, path: str) -> str:
        return f"{self.client.meta.endpoint_url}/{self.bucket}/{path}"


def get_storage() -> StorageBackend:
    settings = get_settings()
    if settings.STORAGE_BACKEND.lower() == "s3":
        return S3Storage()
    return LocalStorage()
