from fastapi import HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.user import User


async def get_api_key_user(request: Request, db: AsyncSession) -> User | None:
    _ = db
    api_key = request.headers.get("X-API-Key")
    if not api_key:
        return None
    if api_key not in get_settings().API_KEYS:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")
    return User(
        user_id="service-account",
        username="service-account",
        password_hash="",
        email="service@example.local",
        role="admin",
    )
