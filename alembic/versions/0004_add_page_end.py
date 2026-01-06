"""Add page end to reading parts.

Revision ID: 0004_add_page_end
Revises: 0003_add_session_seconds
Create Date: 2026-01-06 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = "0004_add_page_end"
down_revision = "0003_add_session_seconds"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add page end column to reading parts."""
    op.add_column(
        "reading_parts",
        sa.Column("page_end", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    """Drop page end column from reading parts."""
    op.drop_column("reading_parts", "page_end")
