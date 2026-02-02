"""Add algorithm training attempts.

Revision ID: 0008_add_algorithm_training_attempts
Revises: 0007_add_algorithm_group_title_norm
Create Date: 2026-02-02 00:00:00.000000
"""

import sqlalchemy as sa

from alembic import op

revision = "0008_add_algorithm_training_attempts"
down_revision = "0007_add_algorithm_group_title_norm"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create algorithm training attempts table."""
    op.create_table(
        "algorithm_training_attempts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "algorithm_id",
            sa.Integer(),
            sa.ForeignKey("algorithms.id"),
            nullable=False,
        ),
        sa.Column("code_text", sa.Text(), nullable=False),
        sa.Column("gpt_check_json", sa.JSON(), nullable=True),
        sa.Column("rating_1_to_5", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_algorithm_training_attempts_algorithm_id",
        "algorithm_training_attempts",
        ["algorithm_id"],
    )


def downgrade() -> None:
    """Drop algorithm training attempts table."""
    op.drop_index(
        "ix_algorithm_training_attempts_algorithm_id",
        table_name="algorithm_training_attempts",
    )
    op.drop_table("algorithm_training_attempts")
