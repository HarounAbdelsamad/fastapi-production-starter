from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pagination import paginate
from app.core.security import hash_password
from app.models.user import User
from app.schemas.pagination import PaginatedResponse, PaginationParams
from app.schemas.user import UserCreate, UserUpdate
from app.services.audit_service import log_action


async def get_user(db: AsyncSession, user_id: str) -> User | None:
    result = await db.execute(
        select(User).where(User.user_id == user_id.strip(), User.deleted_at.is_(None))
    )
    return result.scalars().first()


async def get_all_users(
    db: AsyncSession,
    params: PaginationParams,
) -> PaginatedResponse:
    return await paginate(
        db, select(User).where(User.deleted_at.is_(None)).order_by(User.user_id), params
    )


async def get_user_by_username(db: AsyncSession, username: str) -> User | None:
    result = await db.execute(
        select(User).where(User.username == username, User.deleted_at.is_(None))
    )
    return result.scalars().first()


async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    result = await db.execute(select(User).where(User.email == email, User.deleted_at.is_(None)))
    return result.scalars().first()


async def create_user(db: AsyncSession, data: UserCreate) -> User | None:
    if await get_user(db, data.user_id):
        return None
    if await get_user_by_username(db, data.username):
        return None
    if await get_user_by_email(db, data.email):
        return None
    user = User(
        user_id=data.user_id,
        username=data.username,
        password_hash=hash_password(data.password),
        email=data.email,
        phone_number=data.phone_number,
        role=data.role,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def update_user(db: AsyncSession, user_id: str, data: UserUpdate) -> User | None:
    user = await get_user(db, user_id)
    if not user:
        return None
    updates = data.model_dump(exclude_unset=True)
    if "password" in updates:
        updates["password_hash"] = hash_password(updates.pop("password"))
    for field, value in updates.items():
        setattr(user, field, value)
    await db.commit()
    await db.refresh(user)
    return user


async def delete_user(db: AsyncSession, user_id: str) -> User | None:
    user = await get_user(db, user_id)
    if not user:
        return None
    user.deleted_at = datetime.utcnow()
    await db.commit()
    await log_action(db, user_id=user.user_id, action="USER_SOFT_DELETE", resource=user.user_id)
    return user
