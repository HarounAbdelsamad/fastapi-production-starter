from datetime import UTC, datetime, timedelta
from uuid import uuid4

import jwt
from fastapi import HTTPException, status

from app.core.config import get_settings
from app.schemas.auth import TokenPayload


def _build_token(subject: str, token_type: str, expires_delta: timedelta) -> str:
    settings = get_settings()
    expire = datetime.now(UTC) + expires_delta
    payload = {
        "sub": subject,
        "type": token_type,
        "jti": str(uuid4()),
        "exp": expire,
        "iat": datetime.now(UTC),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_access_token(subject: str) -> str:
    settings = get_settings()
    return _build_token(
        subject=subject,
        token_type="access",
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )


def create_refresh_token(subject: str) -> str:
    settings = get_settings()
    return _build_token(
        subject=subject,
        token_type="refresh",
        expires_delta=timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )


def create_password_reset_token(subject: str) -> str:
    settings = get_settings()
    return _build_token(
        subject=subject,
        token_type="password_reset",
        expires_delta=timedelta(minutes=settings.PASSWORD_RESET_EXPIRE_MINUTES),
    )


def decode_token(token: str) -> TokenPayload:
    settings = get_settings()
    try:
        data = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        return TokenPayload(**data)
    except jwt.PyJWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        ) from exc
