from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class ApiKey(Base):
    __tablename__ = "api_keys"

    key_id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))
    name: Mapped[str] = mapped_column(String)
    key_prefix: Mapped[str] = mapped_column(String, index=True)
    key_hash: Mapped[str] = mapped_column(String, unique=True, index=True)
    owner_user_id: Mapped[str] = mapped_column(String, index=True)
    scopes: Mapped[str] = mapped_column(String, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, default=None)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, default=None)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, default=None)
