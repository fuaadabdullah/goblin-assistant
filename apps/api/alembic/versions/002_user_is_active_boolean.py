"""Migrate users.is_active from string semantics to boolean.

Revision ID: 002_user_is_active_boolean
Revises: 001_initial_vector_setup
Create Date: 2026-03-09 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "002_user_is_active_boolean"
down_revision = "001_initial_vector_setup"
branch_labels = None
depends_on = None


def _normalize_to_bool_case_expr(column_ref: str) -> str:
    return (
        "CASE "
        f"WHEN {column_ref} IS NULL THEN TRUE "
        f"WHEN lower(CAST({column_ref} AS TEXT)) IN ('1','true','t','yes','y','on') THEN TRUE "
        "ELSE FALSE END"
    )


def upgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name

    if dialect == "postgresql":
        op.execute(
            f"""
            ALTER TABLE users
            ALTER COLUMN is_active TYPE BOOLEAN
            USING {_normalize_to_bool_case_expr('is_active')}
            """
        )
        op.alter_column(
            "users",
            "is_active",
            existing_type=sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        )
        return

    # SQLite and other fallback path: add bool column, backfill, replace original.
    op.add_column(
        "users",
        sa.Column("is_active_bool", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.execute(
        f"""
        UPDATE users
        SET is_active_bool = {_normalize_to_bool_case_expr('is_active')}
        """
    )

    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_column("is_active")
        batch_op.alter_column(
            "is_active_bool",
            new_column_name="is_active",
            existing_type=sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        )


def downgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name

    if dialect == "postgresql":
        op.execute(
            """
            ALTER TABLE users
            ALTER COLUMN is_active TYPE VARCHAR
            USING CASE WHEN is_active THEN 'true' ELSE 'false' END
            """
        )
        op.alter_column(
            "users",
            "is_active",
            existing_type=sa.String(),
            nullable=True,
            server_default=sa.text("'true'"),
        )
        return

    op.add_column(
        "users",
        sa.Column("is_active_str", sa.String(), nullable=True, server_default=sa.text("'true'")),
    )
    op.execute(
        """
        UPDATE users
        SET is_active_str = CASE
            WHEN is_active THEN 'true'
            ELSE 'false'
        END
        """
    )

    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_column("is_active")
        batch_op.alter_column(
            "is_active_str",
            new_column_name="is_active",
            existing_type=sa.String(),
            nullable=True,
            server_default=sa.text("'true'"),
        )
