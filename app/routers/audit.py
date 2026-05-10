"""Audit log endpoints — list and export (admin only)."""

import csv
import io
import json

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.deps import get_current_user
from app.db.database import get_session
from app.models.user import User
from app.services import audit_service

router = APIRouter(prefix="/audit-logs", tags=["Audit"])


def _require_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role not in ("admin", "service-account"):
        from fastapi import HTTPException, status

        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return current_user


@router.get("/")
async def list_audit_logs(
    user_id: str | None = Query(default=None, description="Filter by user ID"),
    limit: int = Query(default=50, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_session),
    _admin: User = Depends(_require_admin),
):
    logs = await audit_service.list_audit_logs(db, user_id=user_id, limit=limit, offset=offset)
    return [
        {
            "id": entry.id,
            "user_id": entry.user_id,
            "action": entry.action,
            "resource": entry.resource,
            "detail": entry.detail,
            "ip_address": entry.ip_address,
            "created_at": entry.created_at.isoformat(),
            "hmac_signature": entry.hmac_signature,
        }
        for entry in logs
    ]


@router.get("/export")
async def export_audit_logs(
    fmt: str = Query(default="jsonl", pattern="^(jsonl|csv)$", alias="format"),
    user_id: str | None = Query(default=None),
    db: AsyncSession = Depends(get_session),
    _admin: User = Depends(_require_admin),
):
    """Export all audit logs as JSONL or CSV.

    Include the `hmac_signature` field so consumers can verify row integrity
    offline using `verify_audit_log()` with the application SECRET_KEY.
    """
    logs = await audit_service.list_audit_logs(db, user_id=user_id, limit=10_000, offset=0)
    settings = get_settings()

    if fmt == "jsonl":
        lines = []
        for entry in logs:
            lines.append(
                json.dumps(
                    {
                        "id": entry.id,
                        "user_id": entry.user_id,
                        "action": entry.action,
                        "resource": entry.resource,
                        "detail": entry.detail,
                        "ip_address": entry.ip_address,
                        "created_at": entry.created_at.isoformat(),
                        "hmac_signature": entry.hmac_signature,
                        "signature_valid": audit_service.verify_audit_log(
                            entry, settings.SECRET_KEY
                        ),
                    }
                )
            )
        content = "\n".join(lines)
        return StreamingResponse(
            iter([content]),
            media_type="application/x-ndjson",
            headers={"Content-Disposition": "attachment; filename=audit-logs.jsonl"},
        )

    # CSV
    output = io.StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=["id", "user_id", "action", "resource", "detail", "ip_address",
                    "created_at", "hmac_signature", "signature_valid"],
    )
    writer.writeheader()
    for entry in logs:
        writer.writerow(
            {
                "id": entry.id,
                "user_id": entry.user_id,
                "action": entry.action,
                "resource": entry.resource or "",
                "detail": entry.detail or "",
                "ip_address": entry.ip_address or "",
                "created_at": entry.created_at.isoformat(),
                "hmac_signature": entry.hmac_signature,
                "signature_valid": audit_service.verify_audit_log(entry, settings.SECRET_KEY),
            }
        )
    output.seek(0)
    return StreamingResponse(
        iter([output.read()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=audit-logs.csv"},
    )
