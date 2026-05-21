"""API key lifecycle management.

Keys use the format ``fpsk_<64-hex-chars>`` (FastAPI Starter Key).
Only the SHA-256 hash is stored; the raw key is returned once at creation.
"""

from __future__ import annotations

import hashlib
import secrets
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.api_key import ApiKey

_PREFIX = "fpsk_"


def _generate_raw_key() -> str:
    return _PREFIX + secrets.token_hex(32)


def _hash_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode()).hexdigest()


def _prefix_display(raw_key: str) -> str:
    """Return the first 12 chars of the key (including fpsk_) for display."""
    return raw_key[:12]


async def issue_api_key(
    db: AsyncSession,
    *,
    owner_user_id: str,
    name: str,
    scopes: list[str],
    expires_days: int | None,
) -> tuple[ApiKey, str]:
    """Create a new API key. Returns (model, raw_key). Store raw_key safely — not recoverable."""
    raw_key = _generate_raw_key()
    expires_at = (
        datetime.now(UTC).replace(tzinfo=None) + timedelta(days=expires_days)
        if expires_days
        else None
    )
    api_key = ApiKey(
        name=name,
        key_prefix=_prefix_display(raw_key),
        key_hash=_hash_key(raw_key),
        owner_user_id=owner_user_id,
        scopes=" ".join(scopes),
        expires_at=expires_at,
    )
    db.add(api_key)
    await db.commit()
    await db.refresh(api_key)
    return api_key, raw_key


async def list_api_keys(db: AsyncSession, owner_user_id: str) -> list[ApiKey]:
    result = await db.execute(
        select(ApiKey)
        .where(ApiKey.owner_user_id == owner_user_id)
        .order_by(ApiKey.created_at.desc())
    )
    return list(result.scalars().all())


async def revoke_api_key(db: AsyncSession, *, key_id: str, owner_user_id: str) -> ApiKey | None:
    result = await db.execute(
        select(ApiKey).where(ApiKey.key_id == key_id, ApiKey.owner_user_id == owner_user_id)
    )
    api_key = result.scalars().first()
    if not api_key:
        return None
    api_key.revoked_at = datetime.utcnow()
    await db.commit()
    return api_key


async def rotate_api_key(
    db: AsyncSession, *, key_id: str, owner_user_id: str
) -> tuple[ApiKey, str] | None:
    """Revoke the old key and issue a new one with the same metadata."""
    result = await db.execute(
        select(ApiKey).where(
            ApiKey.key_id == key_id,
            ApiKey.owner_user_id == owner_user_id,
            ApiKey.revoked_at.is_(None),
        )
    )
    old_key = result.scalars().first()
    if not old_key:
        return None
    old_key.revoked_at = datetime.utcnow()

    raw_key = _generate_raw_key()
    new_key = ApiKey(
        name=old_key.name,
        key_prefix=_prefix_display(raw_key),
        key_hash=_hash_key(raw_key),
        owner_user_id=owner_user_id,
        scopes=old_key.scopes,
        expires_at=old_key.expires_at,
    )
    db.add(new_key)
    await db.commit()
    await db.refresh(new_key)
    return new_key, raw_key


async def authenticate_api_key(db: AsyncSession, raw_key: str) -> ApiKey | None:
    """Verify a raw API key and return its record if valid."""
    if not raw_key.startswith(_PREFIX):
        return None
    key_hash = _hash_key(raw_key)
    result = await db.execute(
        select(ApiKey).where(ApiKey.key_hash == key_hash, ApiKey.revoked_at.is_(None))
    )
    api_key = result.scalars().first()
    if not api_key:
        return None
    if api_key.expires_at and api_key.expires_at < datetime.utcnow():
        return None
    api_key.last_used_at = datetime.utcnow()
    await db.commit()
    return api_key
