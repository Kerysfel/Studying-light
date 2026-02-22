"""Add unique ref indexes for user activity events.

Revision ID: 0016_add_user_activity_event_unique_refs
Revises: 0015_add_user_activity_events
Create Date: 2026-02-22 00:00:00.000000
"""

import sqlalchemy as sa

from alembic import op

revision = "0016_add_user_activity_event_unique_refs"
down_revision = "0015_add_user_activity_events"
branch_labels = None
depends_on = None


def _cleanup_duplicates(ref_column: str) -> None:
    op.execute(
        sa.text(
            f"""
            DELETE FROM user_activity_events
            WHERE id IN (
                SELECT id
                FROM (
                    SELECT
                        id,
                        ROW_NUMBER() OVER (
                            PARTITION BY activity_kind, {ref_column}
                            ORDER BY id DESC
                        ) AS row_num
                    FROM user_activity_events
                    WHERE {ref_column} IS NOT NULL
                ) AS ranked
                WHERE ranked.row_num > 1
            )
            """
        )
    )


def upgrade() -> None:
    """Cleanup existing duplicates and enforce unique refs."""
    _cleanup_duplicates("reading_part_id")
    _cleanup_duplicates("review_attempt_id")
    _cleanup_duplicates("algorithm_review_attempt_id")
    _cleanup_duplicates("algorithm_training_attempt_id")

    op.create_index(
        "uq_user_activity_events_kind_reading_part",
        "user_activity_events",
        ["activity_kind", "reading_part_id"],
        unique=True,
        sqlite_where=sa.text("reading_part_id IS NOT NULL"),
        postgresql_where=sa.text("reading_part_id IS NOT NULL"),
    )
    op.create_index(
        "uq_user_activity_events_kind_review_attempt",
        "user_activity_events",
        ["activity_kind", "review_attempt_id"],
        unique=True,
        sqlite_where=sa.text("review_attempt_id IS NOT NULL"),
        postgresql_where=sa.text("review_attempt_id IS NOT NULL"),
    )
    op.create_index(
        "uq_user_activity_events_kind_algorithm_review_attempt",
        "user_activity_events",
        ["activity_kind", "algorithm_review_attempt_id"],
        unique=True,
        sqlite_where=sa.text("algorithm_review_attempt_id IS NOT NULL"),
        postgresql_where=sa.text("algorithm_review_attempt_id IS NOT NULL"),
    )
    op.create_index(
        "uq_user_activity_events_kind_algorithm_training_attempt",
        "user_activity_events",
        ["activity_kind", "algorithm_training_attempt_id"],
        unique=True,
        sqlite_where=sa.text("algorithm_training_attempt_id IS NOT NULL"),
        postgresql_where=sa.text("algorithm_training_attempt_id IS NOT NULL"),
    )


def downgrade() -> None:
    """Drop unique ref indexes."""
    op.drop_index(
        "uq_user_activity_events_kind_algorithm_training_attempt",
        table_name="user_activity_events",
    )
    op.drop_index(
        "uq_user_activity_events_kind_algorithm_review_attempt",
        table_name="user_activity_events",
    )
    op.drop_index(
        "uq_user_activity_events_kind_review_attempt",
        table_name="user_activity_events",
    )
    op.drop_index(
        "uq_user_activity_events_kind_reading_part",
        table_name="user_activity_events",
    )
