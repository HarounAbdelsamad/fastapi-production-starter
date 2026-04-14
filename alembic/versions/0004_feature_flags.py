"""add feature flags

Revision ID: 0004_feature_flags
Revises: 0003_soft_delete
Create Date: 2026-04-14
"""

import sqlalchemy as sa

from alembic import op

revision = "0004_feature_flags"
down_revision = "0003_soft_delete"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "feature_flags",
        sa.Column("key", sa.String(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("description", sa.String(), nullable=True),
        sa.PrimaryKeyConstraint("key"),
    )


def downgrade() -> None:
    op.drop_table("feature_flags")
