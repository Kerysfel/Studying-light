"""Make user settings per-user.

Revision ID: 0011_user_settings_per_user
Revises: 0010_add_users_table
Create Date: 2026-02-04 00:00:00.000000
"""

import sqlalchemy as sa

from alembic import op

revision = "0011_user_settings_per_user"
down_revision = "0010_add_users_table"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create per-user settings and migrate singleton values."""
    op.create_table(
        "user_settings_new",
        sa.Column(
            "user_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("timezone", sa.String(length=64), nullable=True),
        sa.Column("pomodoro_work_min", sa.Integer(), nullable=True),
        sa.Column("pomodoro_break_min", sa.Integer(), nullable=True),
        sa.Column("daily_goal_weekday_min", sa.Integer(), nullable=True),
        sa.Column("daily_goal_weekend_min", sa.Integer(), nullable=True),
        sa.Column("intervals_days", sa.JSON(), nullable=True),
    )

    conn = op.get_bind()
    inspector = sa.inspect(conn)
    if "user_settings" in inspector.get_table_names():
        legacy = conn.execute(
            sa.text(
                """
                SELECT timezone,
                       pomodoro_work_min,
                       pomodoro_break_min,
                       daily_goal_weekday_min,
                       daily_goal_weekend_min,
                       intervals_days
                FROM user_settings
                LIMIT 1
                """
            )
        ).mappings().first()

        if legacy:
            user_ids = conn.execute(sa.text("SELECT id FROM users")).fetchall()
            for row in user_ids:
                conn.execute(
                    sa.text(
                        """
                        INSERT INTO user_settings_new (
                            user_id,
                            timezone,
                            pomodoro_work_min,
                            pomodoro_break_min,
                            daily_goal_weekday_min,
                            daily_goal_weekend_min,
                            intervals_days
                        ) VALUES (
                            :user_id,
                            :timezone,
                            :pomodoro_work_min,
                            :pomodoro_break_min,
                            :daily_goal_weekday_min,
                            :daily_goal_weekend_min,
                            :intervals_days
                        )
                        """
                    ),
                    {"user_id": row[0], **legacy},
                )

    if "user_settings" in inspector.get_table_names():
        op.drop_table("user_settings")
    op.rename_table("user_settings_new", "user_settings")


def downgrade() -> None:
    """Revert to singleton user settings."""
    op.create_table(
        "user_settings_old",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("timezone", sa.String(length=64), nullable=True),
        sa.Column("pomodoro_work_min", sa.Integer(), nullable=True),
        sa.Column("pomodoro_break_min", sa.Integer(), nullable=True),
        sa.Column("daily_goal_weekday_min", sa.Integer(), nullable=True),
        sa.Column("daily_goal_weekend_min", sa.Integer(), nullable=True),
        sa.Column("intervals_days", sa.JSON(), nullable=True),
    )

    conn = op.get_bind()
    inspector = sa.inspect(conn)
    if "user_settings" in inspector.get_table_names():
        legacy = conn.execute(
            sa.text(
                """
                SELECT timezone,
                       pomodoro_work_min,
                       pomodoro_break_min,
                       daily_goal_weekday_min,
                       daily_goal_weekend_min,
                       intervals_days
                FROM user_settings
                LIMIT 1
                """
            )
        ).mappings().first()
        if legacy:
            conn.execute(
                sa.text(
                    """
                    INSERT INTO user_settings_old (
                        id,
                        timezone,
                        pomodoro_work_min,
                        pomodoro_break_min,
                        daily_goal_weekday_min,
                        daily_goal_weekend_min,
                        intervals_days
                    ) VALUES (
                        1,
                        :timezone,
                        :pomodoro_work_min,
                        :pomodoro_break_min,
                        :daily_goal_weekday_min,
                        :daily_goal_weekend_min,
                        :intervals_days
                    )
                    """
                ),
                legacy,
            )

    if "user_settings" in inspector.get_table_names():
        op.drop_table("user_settings")
    op.rename_table("user_settings_old", "user_settings")
