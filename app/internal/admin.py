from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import require_role
from app.db.database import get_session
from app.models.audit_log import AuditLog
from app.models.user import User
from app.schemas.audit import AuditLogResponse

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get("/dashboard", summary="Admin dashboard placeholder")
async def get_admin_dashboard(
    _user: User = Depends(require_role("admin")),
) -> dict[str, str]:
    return {"message": "Admin Dashboard"}


@router.get("/audit-logs", response_model=list[AuditLogResponse], summary="List audit logs")
async def get_audit_logs(
    db: AsyncSession = Depends(get_session),
    _user: User = Depends(require_role("admin")),
) -> list[AuditLog]:
    result = await db.execute(select(AuditLog).order_by(AuditLog.created_at.desc()).limit(200))
    return list(result.scalars().all())
