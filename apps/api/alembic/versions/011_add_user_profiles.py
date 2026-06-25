"""Add user_profiles table for structured user profile data.

Revision ID: 011_add_user_profiles
Revises: 010_add_memory_state_lifecycle
Create Date: 2026-06-12 00:00:00.000000
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "011_add_user_profiles"
down_revision = "010_add_memory_state_lifecycle"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user_profiles",
        sa.Column(
            "id", UUID(as_uuid=True), nullable=False, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column("user_id", UUID(as_uuid=True), nullable=False),
        sa.Column("goals", JSONB(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("projects", JSONB(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("preferences", JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("key_entities", JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
    )
    op.create_index("idx_user_profiles_user_id", "user_profiles", ["user_id"])
    op.create_index("idx_user_profiles_updated_at", "user_profiles", ["updated_at"])


def downgrade() -> None:
    op.drop_index("idx_user_profiles_updated_at", table_name="user_profiles")
    op.drop_index("idx_user_profiles_user_id", table_name="user_profiles")
    op.drop_table("user_profiles")
