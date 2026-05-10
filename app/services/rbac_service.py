"""RBAC service: role/permission management with hierarchy resolution.

Hierarchy: a role inherits all permissions of its parent role.
Example:  admin → parent=manager → parent=user
          admin has: admin perms + manager perms + user perms
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.role import Permission, Role, RolePermission, UserRole


async def create_role(
    db: AsyncSession,
    *,
    name: str,
    description: str = "",
    parent_role_id: str | None = None,
) -> Role:
    role = Role(name=name, description=description, parent_role_id=parent_role_id)
    db.add(role)
    await db.commit()
    await db.refresh(role)
    return role


async def get_role_by_name(db: AsyncSession, name: str) -> Role | None:
    result = await db.execute(select(Role).where(Role.name == name))
    return result.scalars().first()


async def list_roles(db: AsyncSession) -> list[Role]:
    result = await db.execute(select(Role).order_by(Role.name))
    return list(result.scalars().all())


async def get_or_create_permission(
    db: AsyncSession, *, resource: str, action: str, description: str = ""
) -> Permission:
    result = await db.execute(
        select(Permission).where(Permission.resource == resource, Permission.action == action)
    )
    perm = result.scalars().first()
    if perm:
        return perm
    perm = Permission(resource=resource, action=action, description=description)
    db.add(perm)
    await db.commit()
    await db.refresh(perm)
    return perm


async def assign_permission_to_role(
    db: AsyncSession, *, role_id: str, permission_id: str
) -> RolePermission | None:
    existing = await db.execute(
        select(RolePermission).where(
            RolePermission.role_id == role_id, RolePermission.permission_id == permission_id
        )
    )
    if existing.scalars().first():
        return None
    rp = RolePermission(role_id=role_id, permission_id=permission_id)
    db.add(rp)
    await db.commit()
    return rp


async def grant_role(
    db: AsyncSession, *, user_id: str, role_id: str, granted_by: str | None = None
) -> UserRole:
    existing = await db.execute(
        select(UserRole).where(UserRole.user_id == user_id, UserRole.role_id == role_id)
    )
    if existing.scalars().first():
        return existing.scalars().first()  # type: ignore[return-value]
    ur = UserRole(user_id=user_id, role_id=role_id, granted_by=granted_by)
    db.add(ur)
    await db.commit()
    await db.refresh(ur)
    return ur


async def revoke_role(db: AsyncSession, *, user_id: str, role_id: str) -> bool:
    result = await db.execute(
        select(UserRole).where(UserRole.user_id == user_id, UserRole.role_id == role_id)
    )
    ur = result.scalars().first()
    if not ur:
        return False
    await db.delete(ur)
    await db.commit()
    return True


async def get_user_roles(db: AsyncSession, user_id: str) -> list[UserRole]:
    result = await db.execute(select(UserRole).where(UserRole.user_id == user_id))
    return list(result.scalars().all())


async def _collect_role_permissions(db: AsyncSession, role_id: str, visited: set[str]) -> set[str]:
    """Recursively collect `resource:action` strings for role_id and all ancestors."""
    if role_id in visited:
        return set()
    visited.add(role_id)

    perms: set[str] = set()

    # Own permissions
    result = await db.execute(
        select(RolePermission, Permission)
        .join(Permission, RolePermission.permission_id == Permission.permission_id)
        .where(RolePermission.role_id == role_id)
    )
    for rp, perm in result.all():
        _ = rp
        perms.add(f"{perm.resource}:{perm.action}")

    # Parent role permissions
    role_result = await db.execute(select(Role).where(Role.role_id == role_id))
    role = role_result.scalars().first()
    if role and role.parent_role_id:
        parent_perms = await _collect_role_permissions(db, role.parent_role_id, visited)
        perms.update(parent_perms)

    return perms


# Built-in fallback permissions for legacy User.role strings
_BUILTIN_ROLE_PERMS: dict[str, set[str]] = {
    "admin": {"*:*"},
    "manager": {"users:read", "users:write", "api-keys:read", "roles:read"},
    "user": {"self:read", "self:write", "api-keys:read"},
    "service-account": {"*:*"},
}


async def get_effective_permissions(db: AsyncSession, user_id: str, role: str = "") -> set[str]:
    """Return all effective `resource:action` strings for a user.

    Walks the UserRole → Role → parent chain. Falls back to built-in mapping
    from User.role string if the user has no explicit UserRole entries.
    """
    user_roles = await get_user_roles(db, user_id)
    if not user_roles:
        return _BUILTIN_ROLE_PERMS.get(role, {"self:read", "self:write"})

    perms: set[str] = set()
    visited: set[str] = set()
    for ur in user_roles:
        role_perms = await _collect_role_permissions(db, ur.role_id, visited)
        perms.update(role_perms)
    return perms


async def user_has_permission(
    db: AsyncSession, user_id: str, resource: str, action: str, role: str = ""
) -> bool:
    perms = await get_effective_permissions(db, user_id, role=role)
    return "*:*" in perms or f"{resource}:{action}" in perms or f"{resource}:*" in perms
