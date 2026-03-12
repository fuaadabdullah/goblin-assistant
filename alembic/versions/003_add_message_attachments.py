"""Add message_attachments table for file uploads.

Revision ID: 003_add_message_attachments
Revises: 002_user_is_active_boolean
Create Date: 2026-03-10 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = "003_add_message_attachments"
down_revision = "002_user_is_active_boolean"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "message_attachments",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column(
            "message_id",
            sa.String(),
            sa.ForeignKey("messages.message_id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("filename", sa.String(), nullable=False),
        sa.Column("mime_type", sa.String(), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("storage_key", sa.String(), nullable=False),
        sa.Column("upload_hash", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("message_attachments")
