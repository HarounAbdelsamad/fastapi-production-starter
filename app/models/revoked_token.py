from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class RevokedToken(Base):
    __tablename__ = "revoked_tokens"

    token_id: Mapped[str] = mapped_column(
        String(255), primary_key=True, default=lambda: str(uuid4())
    )
    jti: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    token_type: Mapped[str] = mapped_column(String(255), default="access")
    user_id: Mapped[str] = mapped_column(String(255), index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=False))
    revoked_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), default=datetime.utcnow)
