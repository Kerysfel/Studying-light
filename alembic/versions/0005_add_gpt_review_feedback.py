"""Add GPT review feedback fields.

Revision ID: 0005_add_gpt_review_feedback
Revises: 0004_add_page_end
Create Date: 2026-01-10 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = "0005_add_gpt_review_feedback"
down_revision = "0004_add_page_end"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add GPT feedback columns to review attempts."""
    op.add_column(
        "review_attempts",
        sa.Column("gpt_check_payload", sa.JSON(), nullable=True),
    )
    op.add_column(
        "review_attempts",
        sa.Column("gpt_rating_1_to_5", sa.Integer(), nullable=True),
    )
    op.add_column(
        "review_attempts",
        sa.Column("gpt_score_0_to_100", sa.Integer(), nullable=True),
    )
    op.add_column(
        "review_attempts",
        sa.Column("gpt_verdict", sa.String(length=16), nullable=True),
    )


def downgrade() -> None:
    """Remove GPT feedback columns from review attempts."""
    op.drop_column("review_attempts", "gpt_verdict")
    op.drop_column("review_attempts", "gpt_score_0_to_100")
    op.drop_column("review_attempts", "gpt_rating_1_to_5")
    op.drop_column("review_attempts", "gpt_check_payload")
