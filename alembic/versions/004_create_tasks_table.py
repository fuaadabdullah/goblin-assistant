"""Create tasks table for persistent task/job storage.

Revision ID: 004_create_tasks_table
Revises: 003_add_message_attachments
Create Date: 2026-03-12 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = "004_create_tasks_table"
down_revision = "003_add_message_attachments"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tasks",
        sa.Column("task_id", sa.String(), primary_key=True),
        sa.Column(
            "user_id",
            sa.String(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("status", sa.String(), nullable=False, server_default="pending"),
        sa.Column("task_type", sa.String(), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=True),
        sa.Column("result", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=True),
    )
    op.create_index("ix_tasks_user_id", "tasks", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_tasks_user_id", table_name="tasks")
    op.drop_table("tasks")
