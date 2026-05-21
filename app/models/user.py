from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.pii import mark_pii
from app.db.database import Base
from app.db.mixins import SoftDeleteMixin


@mark_pii("email", "phone_number")
class User(Base, SoftDeleteMixin):
    __tablename__ = "users"

    user_id: Mapped[str] = mapped_column(String(255), primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    email: Mapped[str] = mapped_column(String(255))
    phone_number: Mapped[str | None] = mapped_column(String(255), nullable=True, default="")
    role: Mapped[str] = mapped_column(String(255), default="user")
