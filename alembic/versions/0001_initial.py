"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-04-10
"""

import sqlalchemy as sa

from alembic import op

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("username", sa.String(), nullable=False),
        sa.Column("password_hash", sa.String(), nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("phone_number", sa.String(), nullable=True),
        sa.Column("role", sa.String(), nullable=False, server_default="user"),
        sa.PrimaryKeyConstraint("user_id"),
    )
    op.create_index("ix_users_user_id", "users", ["user_id"], unique=False)
    op.create_index("ix_users_username", "users", ["username"], unique=True)

    op.create_table(
        "revoked_tokens",
        sa.Column("token_id", sa.String(), nullable=False),
        sa.Column("jti", sa.String(), nullable=False),
        sa.Column("token_type", sa.String(), nullable=False, server_default="access"),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("revoked_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("token_id"),
    )
    op.create_index("ix_revoked_tokens_jti", "revoked_tokens", ["jti"], unique=True)
    op.create_index("ix_revoked_tokens_user_id", "revoked_tokens", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_revoked_tokens_user_id", table_name="revoked_tokens")
    op.drop_index("ix_revoked_tokens_jti", table_name="revoked_tokens")
    op.drop_table("revoked_tokens")
    op.drop_index("ix_users_username", table_name="users")
    op.drop_index("ix_users_user_id", table_name="users")
    op.drop_table("users")
