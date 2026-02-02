"""Add mode and metrics to algorithm training attempts.

Revision ID: 0009_add_algorithm_training_metrics
Revises: 0008_add_algorithm_training_attempts
Create Date: 2026-02-02 00:00:00.000000
"""

import sqlalchemy as sa

from alembic import op

revision = "0009_add_algorithm_training_metrics"
down_revision = "0008_add_algorithm_training_attempts"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add training metrics columns."""
    with op.batch_alter_table("algorithm_training_attempts") as batch:
        batch.add_column(
            sa.Column(
                "mode",
                sa.String(length=16),
                nullable=False,
                server_default="memory",
            )
        )
        batch.add_column(sa.Column("accuracy", sa.Float(), nullable=True))
        batch.add_column(sa.Column("duration_sec", sa.Integer(), nullable=True))


def downgrade() -> None:
    """Drop training metrics columns."""
    with op.batch_alter_table("algorithm_training_attempts") as batch:
        batch.drop_column("duration_sec")
        batch.drop_column("accuracy")
        batch.drop_column("mode")
