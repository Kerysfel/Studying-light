"""Add session seconds to reading parts.

Revision ID: 0003_add_session_seconds
Revises: 0002_add_pages_fields
Create Date: 2026-01-06 00:00:00.000000
"""

import sqlalchemy as sa

from alembic import op

revision = "0003_add_session_seconds"
down_revision = "0002_add_pages_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add session seconds column to reading parts."""
    op.add_column(
        "reading_parts",
        sa.Column("session_seconds", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    """Drop session seconds column from reading parts."""
    op.drop_column("reading_parts", "session_seconds")
