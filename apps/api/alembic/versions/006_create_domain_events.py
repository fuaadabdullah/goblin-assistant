"""Create domain_events table for orchestration event log.

Revision ID: 006_create_domain_events
Revises: 005_add_user_sessions
Create Date: 2026-05-29 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "006_create_domain_events"
down_revision = "005_add_user_sessions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "domain_events",
        sa.Column("event_id", sa.String(), nullable=False),
        sa.Column("event_type", sa.String(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(), nullable=False),
        sa.Column("source", sa.String(), nullable=False),
        sa.Column("actor_user_id", sa.String(), nullable=True),
        sa.Column("correlation_id", sa.String(), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint("event_id"),
    )
    op.create_index("ix_domain_events_event_type", "domain_events", ["event_type"])
    op.create_index("ix_domain_events_occurred_at", "domain_events", ["occurred_at"])
    op.create_index("ix_domain_events_actor_user_id", "domain_events", ["actor_user_id"])
    op.create_index("ix_domain_events_correlation_id", "domain_events", ["correlation_id"])
    op.create_index(
        "idx_domain_events_type_occurred",
        "domain_events",
        ["event_type", "occurred_at"],
    )
    op.create_index(
        "idx_domain_events_actor_occurred",
        "domain_events",
        ["actor_user_id", "occurred_at"],
    )
    op.create_index("idx_domain_events_correlation", "domain_events", ["correlation_id"])


def downgrade() -> None:
    op.drop_index("idx_domain_events_correlation", table_name="domain_events")
    op.drop_index("idx_domain_events_actor_occurred", table_name="domain_events")
    op.drop_index("idx_domain_events_type_occurred", table_name="domain_events")
    op.drop_index("ix_domain_events_correlation_id", table_name="domain_events")
    op.drop_index("ix_domain_events_actor_user_id", table_name="domain_events")
    op.drop_index("ix_domain_events_occurred_at", table_name="domain_events")
    op.drop_index("ix_domain_events_event_type", table_name="domain_events")
    op.drop_table("domain_events")
