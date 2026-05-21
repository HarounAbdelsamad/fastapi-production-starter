"""GDPR data helpers — export, pseudonymization, and erasure.

Strategy
--------
* **Export** — collects all data for a user across registered tables and
  returns a JSON-serialisable dict. Add new tables to ``_export_user_data``
  as the schema grows.

* **Pseudonymize** — replaces PII fields (registered via ``@mark_pii``) with
  a deterministic but non-reversible hash. Referential integrity is preserved
  (user_id FK columns are not touched).

* **Hard delete** — removes the user row. Audit logs are retained for
  compliance (they contain user_id but no PII after pseudonymisation). Call
  ``pseudonymize_user`` before ``delete_user_data`` if you want to keep the
  audit trail without PII.
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pii import all_pii_models
from app.models.audit_log import AuditLog
from app.models.user import User


def _pseudo(user_id: str, field: str, secret: str) -> str:
    """Deterministic non-reversible token for a (user, field) pair."""
    raw = f"{user_id}:{field}:{secret}".encode()
    return "deleted-" + hashlib.sha256(raw).hexdigest()[:16]


async def export_user_data(db: AsyncSession, user_id: str) -> dict:
    """Collect all data belonging to *user_id* across registered tables.

    Returns a JSON-serialisable dict. Extend the list of queries here as the
    schema grows — this is the single place that drives the export endpoint.
    """
    from app.models.api_key import ApiKey
    from app.models.oauth_account import OAuthAccount
    from app.models.role import UserRole

    user_row = (await db.execute(select(User).where(User.user_id == user_id))).scalar_one_or_none()
    if not user_row:
        return {}

    api_keys = (
        (await db.execute(select(ApiKey).where(ApiKey.owner_user_id == user_id))).scalars().all()
    )

    oauth_accounts = (
        (await db.execute(select(OAuthAccount).where(OAuthAccount.user_id == user_id)))
        .scalars()
        .all()
    )

    user_roles = (
        (await db.execute(select(UserRole).where(UserRole.user_id == user_id))).scalars().all()
    )

    audit_logs = (
        (
            await db.execute(
                select(AuditLog).where(AuditLog.user_id == user_id).order_by(AuditLog.created_at)
            )
        )
        .scalars()
        .all()
    )

    return {
        "exported_at": datetime.now(UTC).isoformat(),
        "user_id": user_id,
        "profile": {
            "username": user_row.username,
            "email": user_row.email,
            "phone_number": user_row.phone_number,
            "role": user_row.role,
        },
        "api_keys": [
            {
                "key_id": k.key_id,
                "name": k.name,
                "key_prefix": k.key_prefix,
                "scopes": k.scopes,
                "created_at": k.created_at.isoformat(),
                "last_used_at": k.last_used_at.isoformat() if k.last_used_at else None,
                "revoked_at": k.revoked_at.isoformat() if k.revoked_at else None,
            }
            for k in api_keys
        ],
        "oauth_accounts": [
            {
                "provider": a.provider,
                "provider_email": a.provider_email,
                "provider_username": a.provider_username,
            }
            for a in oauth_accounts
        ],
        "roles": [{"role_id": r.role_id} for r in user_roles],
        "audit_logs": [
            {
                "action": log.action,
                "resource": log.resource,
                "created_at": log.created_at.isoformat(),
            }
            for log in audit_logs
        ],
    }


async def pseudonymize_user(db: AsyncSession, user_id: str, *, secret: str) -> None:
    """Replace PII fields on all registered models with deterministic hashes.

    After this call the user's PII is gone but referential integrity (FKs
    that reference user_id) is preserved. Audit logs are intentionally kept.
    """
    for model_cls, pii_fields in all_pii_models().items():
        if not hasattr(model_cls, "__table__"):
            continue
        pk_col = model_cls.__table__.primary_key.columns.values()
        user_fk = next(
            (c for c in model_cls.__table__.columns if c.name == "user_id"),
            None,
        )
        if user_fk is None:
            # Check if the model IS the user table (PK = user_id)
            is_user_table = any(c.name == "user_id" for c in pk_col)
            if not is_user_table:
                continue
            values = {f: _pseudo(user_id, f, secret) for f in pii_fields}
            await db.execute(update(model_cls).where(model_cls.user_id == user_id).values(**values))
        else:
            values = {f: _pseudo(user_id, f, secret) for f in pii_fields}
            await db.execute(update(model_cls).where(user_fk == user_id).values(**values))

    # Mark the user record's deleted_at so soft-delete queries exclude it
    await db.execute(
        update(User)
        .where(User.user_id == user_id)
        .values(deleted_at=datetime.now(UTC).replace(tzinfo=None))
    )
    await db.commit()


async def delete_user_data(db: AsyncSession, user_id: str) -> bool:
    """Hard-delete the user row.

    Audit logs are NOT deleted — they are append-only compliance records.
    Call ``pseudonymize_user`` first if you want to strip PII from logs.

    Returns True if the user existed and was deleted, False if not found.
    """
    from sqlalchemy import delete as sql_delete

    from app.models.api_key import ApiKey
    from app.models.oauth_account import OAuthAccount
    from app.models.role import UserRole

    user = (await db.execute(select(User).where(User.user_id == user_id))).scalar_one_or_none()
    if not user:
        return False

    # Remove associated rows first (no cascade configured)
    await db.execute(sql_delete(UserRole).where(UserRole.user_id == user_id))
    await db.execute(sql_delete(ApiKey).where(ApiKey.owner_user_id == user_id))
    await db.execute(sql_delete(OAuthAccount).where(OAuthAccount.user_id == user_id))
    await db.execute(sql_delete(User).where(User.user_id == user_id))
    await db.commit()
    return True
