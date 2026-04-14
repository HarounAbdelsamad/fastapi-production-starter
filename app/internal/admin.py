from fastapi import APIRouter, Depends

from app.core.permissions import require_role
from app.models.user import User

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get("/dashboard", summary="Admin dashboard placeholder")
async def get_admin_dashboard(
    _user: User = Depends(require_role("admin")),
) -> dict[str, str]:
    return {"message": "Admin Dashboard"}
