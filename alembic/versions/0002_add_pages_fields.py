"""Add pages fields.

Revision ID: 0002_add_pages_fields
Revises: 0001_initial_schema
Create Date: 2026-01-02 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = "0002_add_pages_fields"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add pages fields to books and reading parts."""
    op.add_column("books", sa.Column("pages_total", sa.Integer(), nullable=True))
    op.add_column(
        "reading_parts",
        sa.Column("pages_read", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    """Drop pages fields from books and reading parts."""
    op.drop_column("reading_parts", "pages_read")
    op.drop_column("books", "pages_total")
