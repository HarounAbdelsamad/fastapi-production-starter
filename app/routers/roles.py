from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.core.permissions import require_role
from app.db.database import get_session
from app.models.role import Role
from app.models.user import User
from app.schemas.role import (
    EffectivePermissionsResponse,
    GrantRoleRequest,
    RoleCreate,
    RoleResponse,
    UserRoleResponse,
)
from app.services.rbac_service import (
    create_role,
    get_effective_permissions,
    get_role_by_name,
    get_user_roles,
    grant_role,
    list_roles,
    revoke_role,
)

router = APIRouter(tags=["Roles & Permissions"])


# ── Role management (admin only) ───────────────────────────────────────────


@router.get("/roles", response_model=list[RoleResponse])
async def list_all_roles(
    _admin: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_session),
) -> list[RoleResponse]:
    roles = await list_roles(db)
    return [RoleResponse.model_validate(r) for r in roles]


@router.post("/roles", response_model=RoleResponse, status_code=status.HTTP_201_CREATED)
async def create_new_role(
    body: RoleCreate,
    _admin: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_session),
) -> RoleResponse:
    existing = await get_role_by_name(db, body.name)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Role '{body.name}' already exists",
        )
    if body.parent_role_id:
        parent = await db.execute(select(Role).where(Role.role_id == body.parent_role_id))
        if not parent.scalars().first():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Parent role not found"
            )
    role = await create_role(
        db, name=body.name, description=body.description, parent_role_id=body.parent_role_id
    )
    return RoleResponse.model_validate(role)


# ── User role assignment ────────────────────────────────────────────────────


@router.get("/users/{user_id}/roles", response_model=list[UserRoleResponse])
async def get_user_role_list(
    user_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
) -> list[UserRoleResponse]:
    if current_user.role != "admin" and current_user.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    user_roles = await get_user_roles(db, user_id)
    responses: list[UserRoleResponse] = []
    for ur in user_roles:
        role_res = await db.execute(select(Role).where(Role.role_id == ur.role_id))
        role = role_res.scalars().first()
        responses.append(
            UserRoleResponse(
                user_id=ur.user_id,
                role_id=ur.role_id,
                role_name=role.name if role else ur.role_id,
                granted_by=ur.granted_by,
                granted_at=ur.granted_at,
            )
        )
    return responses


@router.post(
    "/users/{user_id}/roles", response_model=UserRoleResponse, status_code=status.HTTP_201_CREATED
)
async def assign_role(
    user_id: str,
    body: GrantRoleRequest,
    admin: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_session),
) -> UserRoleResponse:
    role_res = await db.execute(select(Role).where(Role.role_id == body.role_id))
    role = role_res.scalars().first()
    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")
    ur = await grant_role(db, user_id=user_id, role_id=body.role_id, granted_by=admin.user_id)
    return UserRoleResponse(
        user_id=ur.user_id,
        role_id=ur.role_id,
        role_name=role.name,
        granted_by=ur.granted_by,
        granted_at=ur.granted_at,
    )


@router.delete("/users/{user_id}/roles/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_role(
    user_id: str,
    role_id: str,
    _admin: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_session),
) -> None:
    removed = await revoke_role(db, user_id=user_id, role_id=role_id)
    if not removed:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Role assignment not found"
        )


# ── Effective permissions ────────────────────────────────────────────────────


@router.get("/users/{user_id}/permissions", response_model=EffectivePermissionsResponse)
async def get_permissions(
    user_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
) -> EffectivePermissionsResponse:
    if current_user.role != "admin" and current_user.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    user_res = await db.execute(
        select(User).where(User.user_id == user_id, User.deleted_at.is_(None))
    )
    target_user = user_res.scalars().first()
    if not target_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    perms = await get_effective_permissions(db, user_id, role=target_user.role)
    return EffectivePermissionsResponse(user_id=user_id, permissions=sorted(perms))
