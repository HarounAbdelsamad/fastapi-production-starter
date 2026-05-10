"""GDPR compliance endpoints.

* GET  /api/v1/users/me/export           — authenticated user exports their own data
* POST /api/v1/users/{user_id}/pseudonymize — admin: replace PII with hashes, keep audit trail
* DELETE /api/v1/users/{user_id}/erase   — admin: hard-delete all user data

See docs/compliance/gdpr.md for the full GDPR strategy.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.deps import get_current_user
from app.db.database import get_session
from app.models.user import User
from app.services import gdpr_service

router = APIRouter(tags=["GDPR"])


def _require_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role not in ("admin", "service-account"):
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return current_user


@router.get("/users/me/export")
async def export_my_data(
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Return a JSON bundle of all data the platform holds about the requesting user.

    Covers: profile, API keys (metadata only), OAuth accounts, roles, and
    the last 1 000 audit log entries. This satisfies the GDPR Art. 15 right
    to access and Art. 20 right to data portability.
    """
    return await gdpr_service.export_user_data(db, current_user.user_id)


@router.post("/users/{user_id}/pseudonymize", status_code=status.HTTP_204_NO_CONTENT)
async def pseudonymize_user(
    user_id: str,
    db: AsyncSession = Depends(get_session),
    _admin: User = Depends(_require_admin),
):
    """Replace PII fields on all registered tables with deterministic hashes.

    The user record is soft-deleted. Audit logs are retained (the user_id FK
    is preserved; the PII fields on the User row are scrubbed). This satisfies
    GDPR Art. 17 when hard deletion is not possible due to retention obligations.
    """
    settings = get_settings()
    await gdpr_service.pseudonymize_user(db, user_id, secret=settings.SECRET_KEY)


@router.delete("/users/{user_id}/erase", status_code=status.HTTP_204_NO_CONTENT)
async def erase_user(
    user_id: str,
    db: AsyncSession = Depends(get_session),
    _admin: User = Depends(_require_admin),
):
    """Hard-delete all data for a user (GDPR Art. 17 right to erasure).

    Removes the user row plus API keys, OAuth accounts, and role assignments.
    Audit logs are NOT deleted — they are compliance records. Call
    /pseudonymize first if you need to strip PII from audit logs while
    retaining the audit trail.
    """
    deleted = await gdpr_service.delete_user_data(db, user_id)
    if not deleted:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="User not found")
