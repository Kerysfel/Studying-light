"""Add password reset requests table.

Revision ID: 0013_add_password_reset_requests
Revises: 0012_scope_domain_data_by_user
Create Date: 2026-02-09 00:00:00.000000
"""

import sqlalchemy as sa

from alembic import op

revision = "0013_add_password_reset_requests"
down_revision = "0012_scope_domain_data_by_user"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create password reset requests table."""
    op.create_table(
        "password_reset_requests",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "user_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.String(length=32),
            nullable=False,
            server_default=sa.text("'requested'"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )
    op.create_index(
        "ix_password_reset_requests_user_id",
        "password_reset_requests",
        ["user_id"],
        unique=False,
    )


def downgrade() -> None:
    """Drop password reset requests table."""
    op.drop_index("ix_password_reset_requests_user_id", table_name="password_reset_requests")
    op.drop_table("password_reset_requests")
