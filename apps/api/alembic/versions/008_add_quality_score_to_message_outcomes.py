"""Add quality_score column to message_outcomes table.

quality_score is an additive per-message score computed from all feedback
signals that arrive for that message:
    copy            +3
    thumbs_up       +5
    continue        +2
    model_switch    -2
    regenerate      -3
    delete          -4
    provider_switch -5
    thumbs_down     -5

The LearningApplicator joins message_outcomes to read this score and passes
a proportional float reward to the bandit, replacing the fixed binary ±1.

Revision ID: 008_add_quality_score_to_message_outcomes
Revises: 007_create_feedback_events
Create Date: 2026-06-10 00:00:00.000000
"""

import sqlalchemy as sa
from alembic import op

revision = "008_add_quality_score_to_message_outcomes"
down_revision = "007_create_feedback_events"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "message_outcomes",
        sa.Column(
            "quality_score",
            sa.Float(),
            nullable=False,
            server_default=sa.text("0.0"),
        ),
    )


def downgrade() -> None:
    op.drop_column("message_outcomes", "quality_score")
