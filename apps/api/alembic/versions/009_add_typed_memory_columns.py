"""Add typed memory columns to memory_facts.

Revision ID: 009_add_typed_memory_columns
Revises: 008_add_quality_score_to_message_outcomes
Create Date: 2026-06-11 00:00:00.000000
"""

import sqlalchemy as sa

from alembic import op

revision = "009_add_typed_memory_columns"
down_revision = "008_add_quality_score_to_message_outcomes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("memory_facts", sa.Column("memory_type", sa.String(), nullable=True))
    op.add_column("memory_facts", sa.Column("source_kind", sa.String(), nullable=True))
    op.add_column("memory_facts", sa.Column("source_id", sa.String(), nullable=True))
    op.add_column(
        "memory_facts",
        sa.Column("salience_score", sa.Float(), nullable=True, server_default=sa.text("0.0")),
    )
    op.add_column(
        "memory_facts",
        sa.Column("confidence", sa.Float(), nullable=True, server_default=sa.text("0.0")),
    )
    op.add_column(
        "memory_facts",
        sa.Column("sensitivity_level", sa.String(), nullable=True, server_default=sa.text("'low'")),
    )
    op.add_column(
        "memory_facts",
        sa.Column("retention_days", sa.Integer(), nullable=True, server_default=sa.text("365")),
    )
    op.add_column("memory_facts", sa.Column("expires_at", sa.DateTime(), nullable=True))
    op.add_column("memory_facts", sa.Column("last_accessed_at", sa.DateTime(), nullable=True))
    op.add_column(
        "memory_facts",
        sa.Column("confirmation_count", sa.Integer(), nullable=True, server_default=sa.text("0")),
    )
    op.add_column(
        "memory_facts",
        sa.Column(
            "is_archived",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.add_column("memory_facts", sa.Column("related_memory_ids", sa.JSON(), nullable=True))
    op.add_column("memory_facts", sa.Column("entity_refs", sa.JSON(), nullable=True))
    op.add_column("memory_facts", sa.Column("updated_at", sa.DateTime(), nullable=True))

    op.create_index(
        "idx_memory_facts_memory_type",
        "memory_facts",
        ["memory_type"],
    )
    op.create_index(
        "idx_memory_facts_salience_score",
        "memory_facts",
        ["salience_score"],
    )
    op.create_index(
        "idx_memory_facts_expires_at",
        "memory_facts",
        ["expires_at"],
    )


def downgrade() -> None:
    op.drop_index("idx_memory_facts_expires_at", table_name="memory_facts")
    op.drop_index("idx_memory_facts_salience_score", table_name="memory_facts")
    op.drop_index("idx_memory_facts_memory_type", table_name="memory_facts")

    op.drop_column("memory_facts", "updated_at")
    op.drop_column("memory_facts", "entity_refs")
    op.drop_column("memory_facts", "related_memory_ids")
    op.drop_column("memory_facts", "is_archived")
    op.drop_column("memory_facts", "confirmation_count")
    op.drop_column("memory_facts", "last_accessed_at")
    op.drop_column("memory_facts", "expires_at")
    op.drop_column("memory_facts", "retention_days")
    op.drop_column("memory_facts", "sensitivity_level")
    op.drop_column("memory_facts", "confidence")
    op.drop_column("memory_facts", "salience_score")
    op.drop_column("memory_facts", "source_id")
    op.drop_column("memory_facts", "source_kind")
    op.drop_column("memory_facts", "memory_type")
