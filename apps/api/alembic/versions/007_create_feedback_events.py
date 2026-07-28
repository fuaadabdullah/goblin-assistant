"""Create feedback_events and message_outcomes tables for feedback loops.

Revision ID: 007_create_feedback_events
Revises: 006_create_domain_events
Create Date: 2026-06-10 00:00:00.000000
"""

import sqlalchemy as sa
from alembic import op

revision = "007_create_feedback_events"
down_revision = "006_create_domain_events"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- feedback_events table ---
    op.create_table(
        "feedback_events",
        sa.Column("event_id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("conversation_id", sa.String(), nullable=False),
        sa.Column("message_id", sa.String(), nullable=False),
        sa.Column("request_id", sa.String(), nullable=True),
        sa.Column(
            "signal", sa.String(), nullable=False
        ),  # thumbs_up, thumbs_down, regenerate, delete, continue, provider_switch, model_switch, copy
        sa.Column("rating", sa.Integer(), nullable=True),  # +1 or -1 for thumbs
        sa.Column("department", sa.String(), nullable=True),
        sa.Column("provider", sa.String(), nullable=True),
        sa.Column("model", sa.String(), nullable=True),
        sa.Column("task_type", sa.String(), nullable=True),
        sa.Column("intent_label", sa.String(), nullable=True),
        sa.Column("complexity_score", sa.Float(), nullable=True),
        sa.Column("previous_provider", sa.String(), nullable=True),
        sa.Column("previous_model", sa.String(), nullable=True),
        sa.Column("weight", sa.Float(), nullable=False, server_default=sa.text("1.0")),
        sa.Column(
            "applied_to_bandit", sa.Boolean(), nullable=False, server_default=sa.text("true")
        ),
        sa.Column(
            "applied_to_router", sa.Boolean(), nullable=False, server_default=sa.text("true")
        ),
        sa.Column(
            "applied_to_profile", sa.Boolean(), nullable=False, server_default=sa.text("true")
        ),
        sa.Column("metadata", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("event_id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
    )
    op.create_index("ix_feedback_events_user_id", "feedback_events", ["user_id"])
    op.create_index("ix_feedback_events_message_id", "feedback_events", ["message_id"])
    op.create_index("ix_feedback_events_request_id", "feedback_events", ["request_id"])
    op.create_index("ix_feedback_events_signal", "feedback_events", ["signal"])
    op.create_index("ix_feedback_events_department", "feedback_events", ["department"])
    op.create_index("ix_feedback_events_provider", "feedback_events", ["provider"])
    op.create_index(
        "idx_feedback_events_user_created",
        "feedback_events",
        ["user_id", "created_at"],
    )
    op.create_index(
        "idx_feedback_events_signal_created",
        "feedback_events",
        ["signal", "created_at"],
    )
    op.create_index(
        "idx_feedback_events_dept_created",
        "feedback_events",
        ["department", "created_at"],
    )
    op.create_index(
        "idx_feedback_events_provider_created",
        "feedback_events",
        ["provider", "created_at"],
    )

    # --- message_outcomes table ---
    op.create_table(
        "message_outcomes",
        sa.Column("outcome_id", sa.String(), nullable=False),
        sa.Column("message_id", sa.String(), nullable=False),
        sa.Column("conversation_id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("was_regenerated", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("was_deleted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("was_copied", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column(
            "conversation_continued", sa.Boolean(), nullable=False, server_default=sa.text("false")
        ),
        sa.Column(
            "provider_switched_before_next",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "model_switched_before_next",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column("next_message_id", sa.String(), nullable=True),
        sa.Column("previous_provider", sa.String(), nullable=True),
        sa.Column("previous_model", sa.String(), nullable=True),
        sa.Column("new_provider", sa.String(), nullable=True),
        sa.Column("new_model", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("outcome_id"),
        sa.ForeignKeyConstraint(["message_id"], ["messages.message_id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
    )
    op.create_index("ix_message_outcomes_message_id", "message_outcomes", ["message_id"])
    op.create_index("ix_message_outcomes_conversation_id", "message_outcomes", ["conversation_id"])
    op.create_index("ix_message_outcomes_user_id", "message_outcomes", ["user_id"])
    op.create_index(
        "idx_message_outcomes_message",
        "message_outcomes",
        ["message_id"],
    )
    op.create_index(
        "idx_message_outcomes_conversation",
        "message_outcomes",
        ["conversation_id", "created_at"],
    )


def downgrade() -> None:
    # Drop message_outcomes indexes and table
    op.drop_index("idx_message_outcomes_conversation", table_name="message_outcomes")
    op.drop_index("idx_message_outcomes_message", table_name="message_outcomes")
    op.drop_index("ix_message_outcomes_user_id", table_name="message_outcomes")
    op.drop_index("ix_message_outcomes_conversation_id", table_name="message_outcomes")
    op.drop_index("ix_message_outcomes_message_id", table_name="message_outcomes")
    op.drop_table("message_outcomes")

    # Drop feedback_events indexes and table
    op.drop_index("idx_feedback_events_provider_created", table_name="feedback_events")
    op.drop_index("idx_feedback_events_dept_created", table_name="feedback_events")
    op.drop_index("idx_feedback_events_signal_created", table_name="feedback_events")
    op.drop_index("idx_feedback_events_user_created", table_name="feedback_events")
    op.drop_index("ix_feedback_events_provider", table_name="feedback_events")
    op.drop_index("ix_feedback_events_department", table_name="feedback_events")
    op.drop_index("ix_feedback_events_signal", table_name="feedback_events")
    op.drop_index("ix_feedback_events_request_id", table_name="feedback_events")
    op.drop_index("ix_feedback_events_message_id", table_name="feedback_events")
    op.drop_index("ix_feedback_events_user_id", table_name="feedback_events")
    op.drop_table("feedback_events")
