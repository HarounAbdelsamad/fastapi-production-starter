from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class Role(Base):
    __tablename__ = "roles"

    role_id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))
    name: Mapped[str] = mapped_column(String, unique=True, index=True)
    description: Mapped[str] = mapped_column(String, default="")
    parent_role_id: Mapped[str | None] = mapped_column(
        String, ForeignKey("roles.role_id"), nullable=True, default=None
    )


class Permission(Base):
    __tablename__ = "permissions"
    __table_args__ = (UniqueConstraint("resource", "action", name="uq_perm_resource_action"),)

    permission_id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid4())
    )
    resource: Mapped[str] = mapped_column(String, index=True)
    action: Mapped[str] = mapped_column(String)
    description: Mapped[str] = mapped_column(String, default="")


class RolePermission(Base):
    __tablename__ = "role_permissions"
    __table_args__ = (
        UniqueConstraint("role_id", "permission_id", name="uq_role_permission"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))
    role_id: Mapped[str] = mapped_column(String, ForeignKey("roles.role_id"), index=True)
    permission_id: Mapped[str] = mapped_column(
        String, ForeignKey("permissions.permission_id"), index=True
    )


class UserRole(Base):
    __tablename__ = "user_roles"
    __table_args__ = (UniqueConstraint("user_id", "role_id", name="uq_user_role"),)

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(String, index=True)
    role_id: Mapped[str] = mapped_column(String, ForeignKey("roles.role_id"), index=True)
    granted_by: Mapped[str | None] = mapped_column(String, nullable=True, default=None)
    granted_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
