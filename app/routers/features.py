"""Feature flag management endpoints (admin only).

Global flags:   GET/PUT /api/v1/admin/features
Per-subject:    PUT/DELETE /api/v1/admin/features/{key}/overrides/{type}/{id}
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import require_role
from app.db.database import get_session
from app.models.user import User
from app.services import feature_service

router = APIRouter(prefix="/admin/features")

_VALID_SUBJECT_TYPES = {"user", "tenant"}


class FeatureFlagUpdate(BaseModel):
    enabled: bool
    description: str | None = None


class OverrideRequest(BaseModel):
    enabled: bool

    @field_validator("enabled")
    @classmethod
    def must_be_bool(cls, v: bool) -> bool:
        return v


# ---------------------------------------------------------------------------
# Global flags
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Per-subject overrides
# ---------------------------------------------------------------------------


@router.put("/{key}/overrides/{subject_type}/{subject_id}")
async def upsert_override(
    key: str,
    subject_type: str,
    subject_id: str,
    body: OverrideRequest,
    db: AsyncSession = Depends(get_session),
    _user: User = Depends(require_role("admin")),
) -> dict[str, str | bool]:
    if subject_type not in _VALID_SUBJECT_TYPES:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"subject_type must be one of {sorted(_VALID_SUBJECT_TYPES)}",
        )
    override = await feature_service.set_override(
        db,
        key=key,
        subject_type=subject_type,
        subject_id=subject_id,
        enabled=body.enabled,
    )
    return {
        "key": override.key,
        "subject_type": override.subject_type,
        "subject_id": override.subject_id,
        "enabled": override.enabled,
    }


@router.delete(
    "/{key}/overrides/{subject_type}/{subject_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_override(
    key: str,
    subject_type: str,
    subject_id: str,
    db: AsyncSession = Depends(get_session),
    _user: User = Depends(require_role("admin")),
) -> None:
    if subject_type not in _VALID_SUBJECT_TYPES:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"subject_type must be one of {sorted(_VALID_SUBJECT_TYPES)}",
        )
    deleted = await feature_service.delete_override(
        db, key=key, subject_type=subject_type, subject_id=subject_id
    )
    if not deleted:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Override not found")
