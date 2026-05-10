from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.db.database import get_session
from app.models.user import User
from app.schemas.api_key import ApiKeyCreate, ApiKeyCreated, ApiKeyResponse
from app.services.api_key_service import (
    issue_api_key,
    list_api_keys,
    revoke_api_key,
    rotate_api_key,
)

router = APIRouter(prefix="/api-keys", tags=["API Keys"])


@router.post("", response_model=ApiKeyCreated, status_code=status.HTTP_201_CREATED)
async def create_api_key(
    body: ApiKeyCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
) -> ApiKeyCreated:
    """Issue a new API key. The full key is returned **once** — store it securely."""
    api_key, raw_key = await issue_api_key(
        db,
        owner_user_id=current_user.user_id,
        name=body.name,
        scopes=body.scopes,
        expires_days=body.expires_days,
    )
    return ApiKeyCreated(
        key_id=api_key.key_id,
        name=api_key.name,
        key_prefix=api_key.key_prefix,
        scopes=api_key.scopes.split() if api_key.scopes else [],
        created_at=api_key.created_at,
        last_used_at=api_key.last_used_at,
        revoked_at=api_key.revoked_at,
        expires_at=api_key.expires_at,
        key=raw_key,
    )


@router.get("", response_model=list[ApiKeyResponse])
async def get_api_keys(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
) -> list[ApiKeyResponse]:
    """List all API keys owned by the authenticated user."""
    keys = await list_api_keys(db, current_user.user_id)
    return [ApiKeyResponse.from_orm_model(k) for k in keys]


@router.delete("/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_api_key(
    key_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
) -> None:
    """Revoke an API key. Revoked keys are rejected immediately."""
    result = await revoke_api_key(db, key_id=key_id, owner_user_id=current_user.user_id)
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API key not found")


@router.post("/{key_id}/rotate", response_model=ApiKeyCreated)
async def rotate_key(
    key_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
) -> ApiKeyCreated:
    """Rotate an API key — revokes the old one and issues a replacement with the same scopes."""
    result = await rotate_api_key(db, key_id=key_id, owner_user_id=current_user.user_id)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found or already revoked",
        )
    api_key, raw_key = result
    return ApiKeyCreated(
        key_id=api_key.key_id,
        name=api_key.name,
        key_prefix=api_key.key_prefix,
        scopes=api_key.scopes.split() if api_key.scopes else [],
        created_at=api_key.created_at,
        last_used_at=api_key.last_used_at,
        revoked_at=api_key.revoked_at,
        expires_at=api_key.expires_at,
        key=raw_key,
    )
