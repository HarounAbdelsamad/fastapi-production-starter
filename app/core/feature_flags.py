from collections.abc import Callable

from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.database import get_session
from app.services.feature_service import is_enabled


def require_feature(key: str) -> Callable:
    async def checker(db: AsyncSession = Depends(get_session)) -> bool:
        if not get_settings().FEATURE_FLAGS_ENABLED:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Feature not available"
            )
        if not await is_enabled(db, key):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Feature not enabled",
            )
        return True

    return checker
