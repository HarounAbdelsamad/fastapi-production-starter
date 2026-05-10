"""OAuth account linking and user provisioning.

Handles the find-or-create flow for OAuth logins. Each OAuth identity
(provider + provider_user_id) is linked to exactly one local User.
"""

from __future__ import annotations

import secrets

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.oauth_account import OAuthAccount
from app.models.user import User


async def get_oauth_account(
    db: AsyncSession, *, provider: str, provider_user_id: str
) -> OAuthAccount | None:
    result = await db.execute(
        select(OAuthAccount).where(
            OAuthAccount.provider == provider,
            OAuthAccount.provider_user_id == provider_user_id,
        )
    )
    return result.scalars().first()


async def get_or_create_oauth_user(
    db: AsyncSession,
    *,
    provider: str,
    provider_user_id: str,
    email: str,
    username: str,
) -> tuple[User, bool]:
    """Find or create a User for the given OAuth identity.

    Returns (user, created). On first login, a User is provisioned with a
    random password (login via password is disabled for OAuth-only accounts).
    """
    # Check existing OAuth link
    oauth_acct = await get_oauth_account(db, provider=provider, provider_user_id=provider_user_id)
    if oauth_acct:
        result = await db.execute(select(User).where(User.user_id == oauth_acct.user_id))
        user = result.scalars().first()
        if user:
            return user, False

    # Try to find existing user by email
    result = await db.execute(select(User).where(User.email == email, User.deleted_at.is_(None)))
    user = result.scalars().first()

    if not user:
        # Provision new user
        from uuid import uuid4

        safe_username = username.lower().replace(" ", "_")[:30]
        # Ensure unique username by appending random suffix if needed
        existing = await db.execute(select(User).where(User.username == safe_username))
        if existing.scalars().first():
            safe_username = f"{safe_username}_{secrets.token_hex(4)}"

        user = User(
            user_id=str(uuid4()),
            username=safe_username,
            password_hash=hash_password(secrets.token_urlsafe(32)),
            email=email,
            role="user",
        )
        db.add(user)
        await db.flush()
        created = True
    else:
        created = False

    # Link OAuth account
    oauth_acct = OAuthAccount(
        user_id=user.user_id,
        provider=provider,
        provider_user_id=provider_user_id,
        provider_email=email,
        provider_username=username,
    )
    db.add(oauth_acct)
    await db.commit()
    await db.refresh(user)
    return user, created
