"""Add user activity events table.

Revision ID: 0015_add_user_activity_events
Revises: 0014_add_audit_log_and_admin_reset_fields
Create Date: 2026-02-22 00:00:00.000000
"""

import sqlalchemy as sa

from alembic import op

revision = "0015_add_user_activity_events"
down_revision = "0014_add_audit_log_and_admin_reset_fields"
branch_labels = None
depends_on = None

ACTIVITY_KINDS: tuple[str, ...] = (
    "reading_session",
    "review_theory",
    "review_algorithm_theory",
    "algorithm_training_typing",
    "algorithm_training_memory",
)

ACTIVITY_STATUSES: tuple[str, ...] = (
    "completed",
    "aborted",
    "imported",
)

ACTIVITY_SOURCES: tuple[str, ...] = (
    "live",
    "import",
    "backfill",
)


def _as_sql_values(values: tuple[str, ...]) -> str:
    return ", ".join(f"'{value}'" for value in values)


def upgrade() -> None:
    """Create user activity events table."""
    op.create_table(
        "user_activity_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column("activity_kind", sa.String(length=64), nullable=False),
        sa.Column(
            "status",
            sa.String(length=24),
            nullable=False,
            server_default=sa.text("'completed'"),
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_sec", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("score_0_to_100", sa.Integer(), nullable=True),
        sa.Column("rating_1_to_5", sa.Integer(), nullable=True),
        sa.Column("result_label", sa.String(length=32), nullable=True),
        sa.Column("accuracy", sa.Float(), nullable=True),
        sa.Column("book_id", sa.Integer(), nullable=True),
        sa.Column("reading_part_id", sa.Integer(), nullable=True),
        sa.Column("review_item_id", sa.Integer(), nullable=True),
        sa.Column("algorithm_id", sa.Integer(), nullable=True),
        sa.Column("algorithm_review_item_id", sa.Integer(), nullable=True),
        sa.Column("algorithm_training_attempt_id", sa.Integer(), nullable=True),
        sa.Column("review_attempt_id", sa.Integer(), nullable=True),
        sa.Column("algorithm_review_attempt_id", sa.Integer(), nullable=True),
        sa.Column(
            "source",
            sa.String(length=16),
            nullable=False,
            server_default=sa.text("'live'"),
        ),
        sa.Column("meta_json", sa.JSON(), nullable=True),
        sa.CheckConstraint(
            f"activity_kind IN ({_as_sql_values(ACTIVITY_KINDS)})",
            name="ck_user_activity_events_activity_kind",
        ),
        sa.CheckConstraint(
            f"status IN ({_as_sql_values(ACTIVITY_STATUSES)})",
            name="ck_user_activity_events_status",
        ),
        sa.CheckConstraint(
            f"source IN ({_as_sql_values(ACTIVITY_SOURCES)})",
            name="ck_user_activity_events_source",
        ),
        sa.CheckConstraint(
            "duration_sec IS NULL OR duration_sec >= 0",
            name="ck_user_activity_events_duration_non_negative",
        ),
        sa.CheckConstraint(
            "rating_1_to_5 IS NULL OR (rating_1_to_5 >= 1 AND rating_1_to_5 <= 5)",
            name="ck_user_activity_events_rating_range",
        ),
        sa.CheckConstraint(
            "score_0_to_100 IS NULL OR (score_0_to_100 >= 0 AND score_0_to_100 <= 100)",
            name="ck_user_activity_events_score_range",
        ),
        sa.CheckConstraint(
            "started_at IS NULL OR ended_at IS NULL OR ended_at >= started_at",
            name="ck_user_activity_events_time_order",
        ),
    )

    op.create_index(
        "idx_user_activity_events_user_id",
        "user_activity_events",
        ["user_id"],
    )
    op.create_index(
        "idx_user_activity_events_activity_kind",
        "user_activity_events",
        ["activity_kind"],
    )
    op.create_index(
        "idx_user_activity_events_status",
        "user_activity_events",
        ["status"],
    )
    op.create_index(
        "idx_user_activity_events_created_at",
        "user_activity_events",
        ["created_at"],
    )
    op.create_index(
        "idx_user_activity_events_user_kind_created_at",
        "user_activity_events",
        ["user_id", "activity_kind", "created_at"],
    )
    op.create_index(
        "idx_user_activity_events_user_created_at",
        "user_activity_events",
        ["user_id", "created_at"],
    )


def downgrade() -> None:
    """Drop user activity events table."""
    op.drop_index(
        "idx_user_activity_events_user_created_at",
        table_name="user_activity_events",
    )
    op.drop_index(
        "idx_user_activity_events_user_kind_created_at",
        table_name="user_activity_events",
    )
    op.drop_index(
        "idx_user_activity_events_created_at",
        table_name="user_activity_events",
    )
    op.drop_index(
        "idx_user_activity_events_status",
        table_name="user_activity_events",
    )
    op.drop_index(
        "idx_user_activity_events_activity_kind",
        table_name="user_activity_events",
    )
    op.drop_index(
        "idx_user_activity_events_user_id",
        table_name="user_activity_events",
    )
    op.drop_table("user_activity_events")
