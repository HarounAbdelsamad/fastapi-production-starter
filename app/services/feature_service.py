"""Feature flag service.

Evaluation priority (highest → lowest):
1. Per-user override  (``FeatureFlagOverride`` where ``subject_type="user"``)
2. Per-tenant override (``subject_type="tenant"``)
3. Global flag         (``FeatureFlag.enabled``)

Results are cached in Redis (when ``CACHE_ENABLED=true``) with a 60-second TTL
so that repeated calls within a request burst don't hit the database.
Cache is invalidated on every ``set_flag`` / ``set_override`` write.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.feature_flag import FeatureFlag, FeatureFlagOverride

_CACHE_TTL = 60  # seconds


def _flag_cache_key(key: str) -> str:
    return f"ff:{key}"


def _override_cache_key(key: str, subject_type: str, subject_id: str) -> str:
    return f"ff:{key}:{subject_type}:{subject_id}"


async def _redis_get(cache_key: str) -> bool | None:
    try:
        from app.core.cache import get_redis

        redis = await get_redis()
        if redis is None:
            return None
        raw = await redis.get(cache_key)
        if raw is not None:
            return raw == "1"
    except Exception:
        pass
    return None


async def _redis_set(cache_key: str, value: bool) -> None:
    try:
        from app.core.cache import get_redis

        redis = await get_redis()
        if redis is not None:
            await redis.set(cache_key, "1" if value else "0", ex=_CACHE_TTL)
    except Exception:
        pass


async def _redis_delete(*cache_keys: str) -> None:
    try:
        from app.core.cache import get_redis

        redis = await get_redis()
        if redis is not None and cache_keys:
            await redis.delete(*cache_keys)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def list_flags(db: AsyncSession) -> list[FeatureFlag]:
    result = await db.execute(select(FeatureFlag).order_by(FeatureFlag.key))
    return list(result.scalars().all())


async def is_enabled(
    db: AsyncSession,
    key: str,
    *,
    user_id: str | None = None,
    tenant_id: str | None = None,
) -> bool:
    """Return whether *key* is enabled for the given context.

    Pass ``user_id`` and/or ``tenant_id`` to evaluate per-subject overrides
    before falling back to the global flag value.
    """
    # 1. User-level override
    if user_id:
        value = await _get_override(db, key, "user", user_id)
        if value is not None:
            return value

    # 2. Tenant-level override
    if tenant_id:
        value = await _get_override(db, key, "tenant", tenant_id)
        if value is not None:
            return value

    # 3. Global flag (with cache)
    return await _get_global(db, key)


async def _get_global(db: AsyncSession, key: str) -> bool:
    cache_key = _flag_cache_key(key)
    cached = await _redis_get(cache_key)
    if cached is not None:
        return cached

    result = await db.execute(select(FeatureFlag).where(FeatureFlag.key == key))
    flag = result.scalars().first()
    value = bool(flag and flag.enabled)
    await _redis_set(cache_key, value)
    return value


async def _get_override(
    db: AsyncSession, key: str, subject_type: str, subject_id: str
) -> bool | None:
    cache_key = _override_cache_key(key, subject_type, subject_id)
    cached = await _redis_get(cache_key)
    if cached is not None:
        return cached

    result = await db.execute(
        select(FeatureFlagOverride).where(
            FeatureFlagOverride.key == key,
            FeatureFlagOverride.subject_type == subject_type,
            FeatureFlagOverride.subject_id == subject_id,
        )
    )
    override = result.scalars().first()
    if override is None:
        return None
    await _redis_set(cache_key, override.enabled)
    return override.enabled


async def set_flag(
    db: AsyncSession,
    *,
    key: str,
    enabled: bool,
    description: str | None = None,
) -> FeatureFlag:
    result = await db.execute(select(FeatureFlag).where(FeatureFlag.key == key))
    flag = result.scalars().first()
    if flag is None:
        flag = FeatureFlag(key=key, enabled=enabled, description=description)
        db.add(flag)
    else:
        flag.enabled = enabled
        if description is not None:
            flag.description = description
    await db.commit()
    await db.refresh(flag)
    await _redis_delete(_flag_cache_key(key))
    return flag


async def set_override(
    db: AsyncSession,
    *,
    key: str,
    subject_type: str,
    subject_id: str,
    enabled: bool,
) -> FeatureFlagOverride:
    """Upsert a per-user or per-tenant override."""
    result = await db.execute(
        select(FeatureFlagOverride).where(
            FeatureFlagOverride.key == key,
            FeatureFlagOverride.subject_type == subject_type,
            FeatureFlagOverride.subject_id == subject_id,
        )
    )
    override = result.scalars().first()
    if override is None:
        override = FeatureFlagOverride(
            key=key, subject_type=subject_type, subject_id=subject_id, enabled=enabled
        )
        db.add(override)
    else:
        override.enabled = enabled
    await db.commit()
    await db.refresh(override)
    await _redis_delete(_override_cache_key(key, subject_type, subject_id))
    return override


async def delete_override(
    db: AsyncSession,
    *,
    key: str,
    subject_type: str,
    subject_id: str,
) -> bool:
    """Remove an override. Returns True if it existed."""
    result = await db.execute(
        select(FeatureFlagOverride).where(
            FeatureFlagOverride.key == key,
            FeatureFlagOverride.subject_type == subject_type,
            FeatureFlagOverride.subject_id == subject_id,
        )
    )
    override = result.scalars().first()
    if override is None:
        return False
    await db.delete(override)
    await db.commit()
    await _redis_delete(_override_cache_key(key, subject_type, subject_id))
    return True
