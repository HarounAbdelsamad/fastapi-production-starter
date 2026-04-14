from collections.abc import Callable

from fastapi import Depends, HTTPException, status

from app.core.deps import get_current_user
from app.models.user import User


def require_role(*roles: str) -> Callable[[User], User]:
    async def checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient role permissions",
            )
        return user

    return checker
