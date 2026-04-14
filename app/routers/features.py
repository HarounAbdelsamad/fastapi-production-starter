from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import require_role
from app.db.database import get_session
from app.models.user import User
from app.services import feature_service

router = APIRouter(prefix="/admin/features")


class FeatureFlagUpdate(BaseModel):
    enabled: bool
    description: str | None = None


@router.get("")
async def list_feature_flags(
    db: AsyncSession = Depends(get_session),
    _user: User = Depends(require_role("admin")),
) -> list[dict[str, str | bool | None]]:
    rows = await feature_service.list_flags(db)
    return [{"key": r.key, "enabled": r.enabled, "description": r.description} for r in rows]


@router.put("/{key}")
async def upsert_feature_flag(
    key: str,
    body: FeatureFlagUpdate,
    db: AsyncSession = Depends(get_session),
    _user: User = Depends(require_role("admin")),
) -> dict[str, str | bool | None]:
    row = await feature_service.set_flag(
        db, key=key, enabled=body.enabled, description=body.description
    )
    return {"key": row.key, "enabled": row.enabled, "description": row.description}
