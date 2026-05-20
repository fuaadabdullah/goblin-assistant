"""Add user_sessions table for persistent session storage.

Revision ID: 005_add_user_sessions
Revises: 004_create_tasks_table
Create Date: 2026-03-12 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "005_add_user_sessions"
down_revision = "004_create_tasks_table"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user_sessions",
        sa.Column("session_id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("is_revoked", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("expires_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("session_id"),
    )
    op.create_index("ix_user_sessions_user_id", "user_sessions", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_user_sessions_user_id", table_name="user_sessions")
    op.drop_table("user_sessions")
