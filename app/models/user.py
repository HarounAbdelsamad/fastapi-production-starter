from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base
from app.db.mixins import SoftDeleteMixin


class User(Base, SoftDeleteMixin):
    __tablename__ = "users"

    user_id: Mapped[str] = mapped_column(String, primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String, unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String)
    email: Mapped[str] = mapped_column(String)
    phone_number: Mapped[str | None] = mapped_column(String, nullable=True, default="")
    role: Mapped[str] = mapped_column(String, default="user")
