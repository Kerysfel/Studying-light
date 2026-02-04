"""Add users table.

Revision ID: 0010_add_users_table
Revises: 0009_add_algorithm_training_metrics
Create Date: 2026-02-04 00:00:00.000000
"""

import sqlalchemy as sa

from alembic import op

revision = "0010_add_users_table"
down_revision = "0009_add_algorithm_training_metrics"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create users table."""
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "is_admin",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "must_change_password",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column("temp_password_hash", sa.String(length=255), nullable=True),
        sa.Column("temp_password_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("temp_password_used_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    """Drop users table."""
    op.drop_table("users")
