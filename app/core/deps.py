from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import decode_token
from app.core.config import get_settings
from app.db.database import get_session
from app.models.revoked_token import RevokedToken
from app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_session),
) -> User:
    payload = decode_token(token)
    if payload.type != "access":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")

    settings = get_settings()
    if settings.TOKEN_REVOCATION_ENABLED:
        revoked = await db.execute(select(RevokedToken).where(RevokedToken.jti == payload.jti))
        if revoked.scalars().first():
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token revoked")

    result = await db.execute(select(User).where(User.user_id == payload.sub))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user
