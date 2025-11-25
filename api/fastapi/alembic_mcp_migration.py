"""Alembic migration for MCP database schema."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    """Create MCP tables."""
    # Create mcp_request table
    op.create_table(
        "mcp_request",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("user_hash", sa.String(16), nullable=False, index=True),
        sa.Column("status", sa.String(20), nullable=False, index=True),
        sa.Column("task_type", sa.String(50)),
        sa.Column("priority", sa.SmallInteger(), default=50),
        sa.Column("provider_hint", sa.String(100)),
        sa.Column("cost_estimate_usd", sa.Float()),
        sa.Column("created_at", sa.DateTime(), default=sa.text("now()")),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            default=sa.text("now()"),
            onupdate=sa.text("now()"),
        ),
        sa.Column("last_provider", sa.String(100)),
        sa.Column("attempts", sa.Integer(), default=0),
        sa.Column("trace_id", sa.String(32)),
    )

    # Create mcp_event table
    op.create_table(
        "mcp_event",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "request_id", postgresql.UUID(as_uuid=True), nullable=False, index=True
        ),
        sa.Column("ts", sa.DateTime(), default=sa.text("now()")),
        sa.Column("event_type", sa.String(50), index=True),
        sa.Column("payload", postgresql.JSONB()),
    )

    # Create mcp_result table
    op.create_table(
        "mcp_result",
        sa.Column("request_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("result", postgresql.JSONB()),
        sa.Column("tokens", sa.Integer()),
        sa.Column("cost_usd", sa.Float()),
        sa.Column("finished_at", sa.DateTime(), default=sa.text("now()")),
    )


def downgrade():
    """Drop MCP tables."""
    op.drop_table("mcp_result")
    op.drop_table("mcp_event")
    op.drop_table("mcp_request")
