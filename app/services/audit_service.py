import hashlib
import hmac
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog


def _canonical(log: AuditLog) -> str:
    """Deterministic string representation of an audit row used for HMAC signing."""
    return "|".join([
        log.id,
        log.user_id,
        log.action,
        log.resource or "",
        log.detail or "",
        log.ip_address or "",
        log.created_at.isoformat(),
    ])


def _sign(log: AuditLog, secret: str) -> str:
    return hmac.new(secret.encode(), _canonical(log).encode(), hashlib.sha256).hexdigest()


def verify_audit_log(log: AuditLog, secret: str) -> bool:
    """Return True if the stored HMAC matches the row contents.

    A False result means the row was modified after write — treat as tampered.
    """
    expected = _sign(log, secret)
    return hmac.compare_digest(expected, log.hmac_signature)


async def log_action(
    db: AsyncSession,
    *,
    user_id: str,
    action: str,
    resource: str | None = None,
    detail: str | None = None,
    ip_address: str | None = None,
    secret: str = "",
) -> AuditLog:
    from app.core.config import get_settings

    if not secret:
        secret = get_settings().SECRET_KEY

    entry = AuditLog(
        id=str(uuid4()),
        user_id=user_id,
        action=action,
        resource=resource,
        detail=detail,
        ip_address=ip_address,
        created_at=datetime.now(UTC).replace(tzinfo=None),
    )
    entry.hmac_signature = _sign(entry, secret)
    db.add(entry)
    await db.commit()
    return entry


async def list_audit_logs(
    db: AsyncSession,
    *,
    user_id: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[AuditLog]:
    stmt = select(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit).offset(offset)
    if user_id:
        stmt = stmt.where(AuditLog.user_id == user_id)
    result = await db.execute(stmt)
    return list(result.scalars().all())
