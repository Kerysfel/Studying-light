"""Add algorithms tables.

Revision ID: 0006_add_algorithms_tables
Revises: 0005_add_gpt_review_feedback
Create Date: 2026-01-10 00:00:00.000000
"""

import sqlalchemy as sa

from alembic import op

revision = "0006_add_algorithms_tables"
down_revision = "0005_add_gpt_review_feedback"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add algorithm-related tables."""
    op.create_table(
        "algorithm_groups",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
    )

    op.create_table(
        "algorithms",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "group_id",
            sa.Integer(),
            sa.ForeignKey("algorithm_groups.id"),
            nullable=False,
        ),
        sa.Column(
            "source_part_id",
            sa.Integer(),
            sa.ForeignKey("reading_parts.id"),
            nullable=True,
        ),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("when_to_use", sa.Text(), nullable=False),
        sa.Column("complexity", sa.String(length=64), nullable=False),
        sa.Column("invariants", sa.JSON(), nullable=False),
        sa.Column("steps", sa.JSON(), nullable=False),
        sa.Column("corner_cases", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
    )
    op.create_index("ix_algorithms_group_id", "algorithms", ["group_id"])
    op.create_index("ix_algorithms_source_part_id", "algorithms", ["source_part_id"])

    op.create_table(
        "algorithm_code_snippets",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "algorithm_id",
            sa.Integer(),
            sa.ForeignKey("algorithms.id"),
            nullable=False,
        ),
        sa.Column("code_kind", sa.String(length=16), nullable=False),
        sa.Column("language", sa.String(length=32), nullable=False),
        sa.Column("code_text", sa.Text(), nullable=False),
        sa.Column(
            "is_reference",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("1"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_algorithm_code_snippets_algorithm_id",
        "algorithm_code_snippets",
        ["algorithm_id"],
    )

    op.create_table(
        "algorithm_review_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "algorithm_id",
            sa.Integer(),
            sa.ForeignKey("algorithms.id"),
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
        "ix_algorithm_review_items_algorithm_id",
        "algorithm_review_items",
        ["algorithm_id"],
    )

    op.create_table(
        "algorithm_review_attempts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "review_item_id",
            sa.Integer(),
            sa.ForeignKey("algorithm_review_items.id"),
            nullable=False,
        ),
        sa.Column("answers", sa.JSON(), nullable=True),
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
        "ix_algorithm_review_attempts_review_item_id",
        "algorithm_review_attempts",
        ["review_item_id"],
    )


def downgrade() -> None:
    """Drop algorithm-related tables."""
    op.drop_index(
        "ix_algorithm_review_attempts_review_item_id",
        table_name="algorithm_review_attempts",
    )
    op.drop_table("algorithm_review_attempts")
    op.drop_index(
        "ix_algorithm_review_items_algorithm_id",
        table_name="algorithm_review_items",
    )
    op.drop_table("algorithm_review_items")
    op.drop_index(
        "ix_algorithm_code_snippets_algorithm_id",
        table_name="algorithm_code_snippets",
    )
    op.drop_table("algorithm_code_snippets")
    op.drop_index("ix_algorithms_source_part_id", table_name="algorithms")
    op.drop_index("ix_algorithms_group_id", table_name="algorithms")
    op.drop_table("algorithms")
    op.drop_table("algorithm_groups")
