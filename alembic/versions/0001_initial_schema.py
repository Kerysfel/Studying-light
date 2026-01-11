"""Initial schema.

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-01-01 00:00:00.000000
"""

import sqlalchemy as sa

from alembic import op

revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Apply the initial schema."""
    op.create_table(
        "books",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("author", sa.String(length=255), nullable=True),
        sa.Column(
            "status",
            sa.String(length=20),
            nullable=False,
            server_default=sa.text("'active'"),
        ),
    )

    op.create_table(
        "reading_parts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("book_id", sa.Integer(), sa.ForeignKey("books.id"), nullable=False),
        sa.Column("part_index", sa.Integer(), nullable=False),
        sa.Column("label", sa.String(length=255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("raw_notes", sa.JSON(), nullable=True),
        sa.Column("gpt_summary", sa.Text(), nullable=True),
        sa.Column("gpt_questions_by_interval", sa.JSON(), nullable=True),
    )
    op.create_index(
        "ix_reading_parts_book_id",
        "reading_parts",
        ["book_id"],
    )

    op.create_table(
        "review_schedule_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "reading_part_id",
            sa.Integer(),
            sa.ForeignKey("reading_parts.id"),
            nullable=False,
        ),
        sa.Column("interval_days", sa.Integer(), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=False),
        sa.Column(
            "status",
            sa.String(length=20),
            nullable=False,
            server_default=sa.text("'planned'"),
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("questions", sa.JSON(), nullable=True),
    )
    op.create_index(
        "ix_review_schedule_items_reading_part_id",
        "review_schedule_items",
        ["reading_part_id"],
    )

    op.create_table(
        "review_attempts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "review_item_id",
            sa.Integer(),
            sa.ForeignKey("review_schedule_items.id"),
            nullable=False,
        ),
        sa.Column("answers", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("gpt_check_result", sa.Text(), nullable=True),
    )
    op.create_index(
        "ix_review_attempts_review_item_id",
        "review_attempts",
        ["review_item_id"],
    )

    op.create_table(
        "user_settings",
        sa.Column(
            "id",
            sa.Integer(),
            primary_key=True,
            server_default=sa.text("1"),
        ),
        sa.Column("timezone", sa.String(length=64), nullable=True),
        sa.Column("pomodoro_work_min", sa.Integer(), nullable=True),
        sa.Column("pomodoro_break_min", sa.Integer(), nullable=True),
        sa.Column("daily_goal_weekday_min", sa.Integer(), nullable=True),
        sa.Column("daily_goal_weekend_min", sa.Integer(), nullable=True),
        sa.Column("intervals_days", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    """Revert the initial schema."""
    op.drop_table("user_settings")
    op.drop_index("ix_review_attempts_review_item_id", table_name="review_attempts")
    op.drop_table("review_attempts")
    op.drop_index(
        "ix_review_schedule_items_reading_part_id",
        table_name="review_schedule_items",
    )
    op.drop_table("review_schedule_items")
    op.drop_index("ix_reading_parts_book_id", table_name="reading_parts")
    op.drop_table("reading_parts")
    op.drop_table("books")
