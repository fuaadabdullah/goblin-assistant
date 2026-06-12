"""Add entity graph tables and scope column to memory_facts.

Revision ID: 010_add_entity_graph_tables
Revises: 009_add_typed_memory_columns
Create Date: 2026-06-11 00:00:00.000000
"""

import sqlalchemy as sa

from alembic import op

revision = "010_add_entity_graph_tables"
down_revision = "009_add_typed_memory_columns"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add scope column to memory_facts
    op.add_column(
        "memory_facts",
        sa.Column("scope", sa.String(), nullable=True, server_default="global"),
    )
    op.create_index("idx_memory_facts_scope", "memory_facts", ["scope"])

    # Create memory_entities table
    op.create_table(
        "memory_entities",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("entity_type", sa.String(), nullable=False),
        sa.Column("entity_value", sa.String(), nullable=False),
        sa.Column("display_name", sa.String(), nullable=True),
        sa.Column("scope", sa.String(), nullable=True, server_default="global"),
        sa.Column("confidence", sa.Float(), nullable=True, server_default=sa.text("1.0")),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("NOW()")),
        sa.UniqueConstraint(
            "user_id", "entity_type", "entity_value", name="uq_entity_user_type_value"
        ),
    )
    op.create_index("idx_memory_entities_user_id", "memory_entities", ["user_id"])
    op.create_index("idx_memory_entities_user_type", "memory_entities", ["user_id", "entity_type"])
    op.create_index("idx_memory_entities_entity_value", "memory_entities", ["entity_value"])

    # Create memory_entity_relations table
    op.create_table(
        "memory_entity_relations",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column(
            "source_entity_id",
            sa.String(),
            sa.ForeignKey("memory_entities.id"),
            nullable=False,
        ),
        sa.Column(
            "target_entity_id",
            sa.String(),
            sa.ForeignKey("memory_entities.id"),
            nullable=False,
        ),
        sa.Column("relation_type", sa.String(), nullable=False),
        sa.Column(
            "memory_fact_id",
            sa.String(),
            sa.ForeignKey("memory_facts.id"),
            nullable=True,
        ),
        sa.Column("confidence", sa.Float(), nullable=True, server_default=sa.text("1.0")),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("NOW()")),
    )
    op.create_index("idx_entity_relations_user_id", "memory_entity_relations", ["user_id"])
    op.create_index(
        "idx_entity_relations_source",
        "memory_entity_relations",
        ["source_entity_id", "relation_type"],
    )
    op.create_index(
        "idx_entity_relations_target",
        "memory_entity_relations",
        ["target_entity_id", "relation_type"],
    )
    op.create_index("idx_entity_relations_fact", "memory_entity_relations", ["memory_fact_id"])


def downgrade() -> None:
    op.drop_index("idx_entity_relations_fact", "memory_entity_relations")
    op.drop_index("idx_entity_relations_target", "memory_entity_relations")
    op.drop_index("idx_entity_relations_source", "memory_entity_relations")
    op.drop_index("idx_entity_relations_user_id", "memory_entity_relations")
    op.drop_table("memory_entity_relations")

    op.drop_index("idx_memory_entities_entity_value", "memory_entities")
    op.drop_index("idx_memory_entities_user_type", "memory_entities")
    op.drop_index("idx_memory_entities_user_id", "memory_entities")
    op.drop_table("memory_entities")

    op.drop_index("idx_memory_facts_scope", "memory_facts")
    op.drop_column("memory_facts", "scope")
