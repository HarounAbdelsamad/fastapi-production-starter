from sqlalchemy import Boolean, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class FeatureFlag(Base):
    __tablename__ = "feature_flags"

    key: Mapped[str] = mapped_column(String(255), primary_key=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)


class FeatureFlagOverride(Base):
    """Per-user or per-tenant override for a feature flag.

    Lookup priority: user override → tenant override → global flag.
    ``subject_type`` is either ``"user"`` or ``"tenant"``.
    """

    __tablename__ = "feature_flag_overrides"
    __table_args__ = (UniqueConstraint("key", "subject_type", "subject_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    key: Mapped[str] = mapped_column(ForeignKey("feature_flags.key"), nullable=False)
    subject_type: Mapped[str] = mapped_column(String(255), nullable=False)  # "user" | "tenant"
    subject_id: Mapped[str] = mapped_column(String(255), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False)
