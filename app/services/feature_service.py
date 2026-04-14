from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.feature_flag import FeatureFlag


async def list_flags(db: AsyncSession) -> list[FeatureFlag]:
    result = await db.execute(select(FeatureFlag).order_by(FeatureFlag.key))
    return list(result.scalars().all())


async def is_enabled(db: AsyncSession, key: str) -> bool:
    result = await db.execute(select(FeatureFlag).where(FeatureFlag.key == key))
    flag = result.scalars().first()
    return bool(flag and flag.enabled)


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
    return flag
