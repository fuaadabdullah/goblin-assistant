"""Add lifecycle state to memory_facts.

Revision ID: 010_add_memory_state_lifecycle
Revises: 009_add_typed_memory_columns
Create Date: 2026-06-11 00:00:01.000000
"""

import sqlalchemy as sa

from alembic import op

revision = "010_add_memory_state_lifecycle"
down_revision = "009_add_typed_memory_columns"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "memory_facts",
        sa.Column(
            "memory_state",
            sa.String(),
            nullable=False,
            server_default=sa.text("'active'"),
        ),
    )
    op.create_index(
        "idx_memory_facts_memory_state",
        "memory_facts",
        ["memory_state"],
    )

    op.execute(
        sa.text(
            """
            UPDATE memory_facts
            SET memory_state = CASE
                WHEN COALESCE(is_archived, false) = true THEN 'archived'
                ELSE 'active'
            END
            """
        )
    )


def downgrade() -> None:
    op.drop_index("idx_memory_facts_memory_state", table_name="memory_facts")
    op.drop_column("memory_facts", "memory_state")
