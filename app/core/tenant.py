from fastapi import Depends, Request

from app.core.deps import get_current_user
from app.models.user import User


async def get_current_tenant(request: Request, user: User = Depends(get_current_user)) -> str:
    token_tenant = request.headers.get("X-Tenant-ID")
    if token_tenant:
        return token_tenant
    return getattr(user, "tenant_id", "default-tenant")
