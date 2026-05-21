"""Role and permission-based access control dependencies.

Two levels of granularity:
- ``require_role(*roles)``          — checks User.role string (legacy / simple)
- ``require_permission(res, action)`` — checks RBAC tables with hierarchy resolution
"""

from collections.abc import Callable

from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.db.database import get_session
from app.models.user import User


def require_role(*roles: str) -> Callable:  # type: ignore[type-arg]
    async def checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient role permissions",
            )
        return user

    return checker


def require_permission(resource: str, action: str) -> Callable:
    """Dependency that resolves the full RBAC hierarchy.

    Falls back to the built-in role→permission mapping when the user has
    no explicit UserRole entries (backward compatible).
    """

    async def checker(
        user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_session),
    ) -> User:
        from app.services.rbac_service import user_has_permission

        allowed = await user_has_permission(db, user.user_id, resource, action, role=user.role)
        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing permission: {resource}:{action}",
            )
        return user

    return checker
