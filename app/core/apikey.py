"""API key authentication.

Checks DB-backed keys (format: fpsk_...) first, then falls back to the
static API_KEYS list in settings for backward compatibility.
"""

from fastapi import HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.user import User


async def get_api_key_user(request: Request, db: AsyncSession) -> User | None:
    api_key = request.headers.get("X-API-Key")
    if not api_key:
        return None

    # DB-backed keys (fpsk_... format)
    if api_key.startswith("fpsk_"):
        from app.services.api_key_service import authenticate_api_key

        db_key = await authenticate_api_key(db, api_key)
        if db_key:
            result = await db.execute(
                select(User).where(User.user_id == db_key.owner_user_id)
            )
            owner = result.scalars().first()
            if owner:
                return owner
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or revoked API key"
        )

    # Backward-compat: static list from settings
    if api_key in get_settings().API_KEYS:
        return User(
            user_id="service-account",
            username="service-account",
            password_hash="",
            email="service@example.local",
            role="admin",
        )

    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")
