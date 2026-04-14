from datetime import UTC, datetime

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import (
    create_access_token,
    create_password_reset_token,
    create_refresh_token,
    decode_token,
)
from app.core.config import get_settings
from app.core.deps import get_current_user, oauth2_scheme
from app.core.email import send_email
from app.core.security import hash_password, verify_password
from app.db.database import get_session
from app.models.revoked_token import RevokedToken
from app.models.user import User
from app.schemas.auth import RefreshTokenRequest, TokenResponse
from app.schemas.password import PasswordResetConfirm, PasswordResetRequest
from app.tasks.email_tasks import send_email_task

router = APIRouter()


async def _revoke_token(
    db: AsyncSession,
    *,
    jti: str,
    token_type: str,
    user_id: str,
    expires_at: datetime,
) -> None:
    db.add(
        RevokedToken(
            jti=jti,
            token_type=token_type,
            user_id=user_id,
            expires_at=expires_at.replace(tzinfo=None),
        )
    )
    await db.commit()


@router.post("/login", response_model=TokenResponse)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_session),
) -> TokenResponse:
    result = await db.execute(select(User).where(User.username == form_data.username))
    user = result.scalars().first()
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    return TokenResponse(
        access_token=create_access_token(user.user_id),
        refresh_token=create_refresh_token(user.user_id),
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_tokens(
    body: RefreshTokenRequest,
    db: AsyncSession = Depends(get_session),
) -> TokenResponse:
    payload = decode_token(body.refresh_token)
    if payload.type != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
        )

    settings = get_settings()
    if settings.TOKEN_REVOCATION_ENABLED:
        revoked = await db.execute(select(RevokedToken).where(RevokedToken.jti == payload.jti))
        if revoked.scalars().first():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token revoked"
            )

    result = await db.execute(select(User).where(User.user_id == payload.sub))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    if settings.TOKEN_REVOCATION_ENABLED:
        await _revoke_token(
            db,
            jti=payload.jti,
            token_type="refresh",
            user_id=payload.sub,
            expires_at=datetime.fromtimestamp(payload.exp, tz=UTC),
        )

    return TokenResponse(
        access_token=create_access_token(user.user_id),
        refresh_token=create_refresh_token(user.user_id),
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    body: RefreshTokenRequest | None = None,
    access_token: str = Depends(oauth2_scheme),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
) -> None:
    settings = get_settings()
    if not settings.TOKEN_REVOCATION_ENABLED:
        return
    access_payload = decode_token(access_token)
    await _revoke_token(
        db,
        jti=access_payload.jti,
        token_type=access_payload.type,
        user_id=current_user.user_id,
        expires_at=datetime.fromtimestamp(access_payload.exp, tz=UTC),
    )
    if body and body.refresh_token:
        payload = decode_token(body.refresh_token)
        if payload.sub == current_user.user_id:
            await _revoke_token(
                db,
                jti=payload.jti,
                token_type=payload.type,
                user_id=payload.sub,
                expires_at=datetime.fromtimestamp(payload.exp, tz=UTC),
            )


@router.post("/password-reset/request", status_code=status.HTTP_202_ACCEPTED)
async def request_password_reset(
    body: PasswordResetRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_session),
) -> dict[str, str]:
    user_result = await db.execute(select(User).where(User.email == body.email))
    user = user_result.scalars().first()
    if not user:
        return {"detail": "If the email exists, a reset message will be sent"}

    token = create_password_reset_token(user.user_id)
    reset_url = f"{get_settings().FRONTEND_URL}/reset-password?token={token}"
    context = {"username": user.username, "reset_url": reset_url}
    settings = get_settings()
    if settings.CELERY_ENABLED:
        send_email_task.delay(user.email, "Password Reset", "reset_password.html", context)
    else:
        background_tasks.add_task(
            send_email,
            user.email,
            "Password Reset",
            "reset_password.html",
            context,
        )
    return {
        "detail": "Password reset requested",
        "reset_token": token,
    }


@router.post("/password-reset/confirm", status_code=status.HTTP_200_OK)
async def confirm_password_reset(
    body: PasswordResetConfirm,
    db: AsyncSession = Depends(get_session),
) -> dict[str, str]:
    payload = decode_token(body.token)
    if payload.type != "password_reset":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid reset token")
    result = await db.execute(select(User).where(User.user_id == payload.sub))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    user.password_hash = hash_password(body.new_password)
    await db.commit()
    return {"detail": "Password updated"}
