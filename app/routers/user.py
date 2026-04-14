from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.db.database import get_session
from app.models.user import User
from app.schemas.pagination import PaginatedResponse, PaginationParams
from app.schemas.user import UserCreate, UserResponse, UserUpdate
from app.services import user_service

router = APIRouter()


@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    body: UserCreate,
    db: AsyncSession = Depends(get_session),
):
    user = await user_service.create_user(db, body)
    if not user:
        raise HTTPException(status.HTTP_409_CONFLICT, detail="User already exists")
    return user


@router.get("/", response_model=PaginatedResponse[UserResponse])
async def list_users(
    params: PaginationParams = Depends(),
    db: AsyncSession = Depends(get_session),
    _current_user: User = Depends(get_current_user),
):
    return await user_service.get_all_users(db, params)


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: str,
    db: AsyncSession = Depends(get_session),
    _current_user: User = Depends(get_current_user),
):
    user = await user_service.get_user(db, user_id)
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


@router.patch("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str,
    body: UserUpdate,
    db: AsyncSession = Depends(get_session),
    _current_user: User = Depends(get_current_user),
):
    user = await user_service.update_user(db, user_id, body)
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: str,
    db: AsyncSession = Depends(get_session),
    _current_user: User = Depends(get_current_user),
):
    user = await user_service.delete_user(db, user_id)
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="User not found")
