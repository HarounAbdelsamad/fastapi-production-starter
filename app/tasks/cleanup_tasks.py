import asyncio
from datetime import datetime

from sqlalchemy import delete

from app.db.database import SessionLocal
from app.models.revoked_token import RevokedToken
from app.worker import celery_app


async def _cleanup() -> int:
    async with SessionLocal() as session:  # type: ignore[misc]
        result = await session.execute(
            delete(RevokedToken).where(RevokedToken.expires_at < datetime.utcnow())
        )
        await session.commit()
        return result.rowcount or 0  # type: ignore[union-attr]


@celery_app.task(name="tasks.cleanup_revoked_tokens")
def cleanup_revoked_tokens() -> int:
    return asyncio.run(_cleanup())
