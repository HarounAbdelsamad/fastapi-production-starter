from datetime import UTC, datetime
from uuid import uuid4

from fastapi import APIRouter, Depends, UploadFile

from app.core.deps import get_current_user
from app.core.storage import get_storage
from app.models.user import User

router = APIRouter()


@router.post("/upload")
async def upload_file(
    file: UploadFile,
    _current_user: User = Depends(get_current_user),
) -> dict[str, str | int]:
    ext = file.filename.rsplit(".", 1)[-1] if file.filename and "." in file.filename else "bin"
    generated = f"{datetime.now(UTC).strftime('%Y%m%d')}/{uuid4().hex}.{ext}"
    storage = get_storage()
    url = await storage.upload(file, generated)
    return {"url": url, "path": generated, "size": file.size or 0}


@router.delete("/{path:path}")
async def delete_file(
    path: str,
    _current_user: User = Depends(get_current_user),
) -> dict[str, str]:
    storage = get_storage()
    await storage.delete(path)
    return {"detail": "Deleted"}
