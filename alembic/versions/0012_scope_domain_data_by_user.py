"""Scope domain data by user.

Revision ID: 0012_scope_domain_data_by_user
Revises: 0011_user_settings_per_user
Create Date: 2026-02-05 00:00:00.000000
"""

import uuid

import sqlalchemy as sa

from alembic import op

revision = "0012_scope_domain_data_by_user"
down_revision = "0011_user_settings_per_user"
branch_labels = None
depends_on = None

DOMAIN_TABLES: list[str] = [
    "books",
    "reading_parts",
    "review_schedule_items",
    "review_attempts",
    "algorithm_groups",
    "algorithms",
    "algorithm_code_snippets",
    "algorithm_review_items",
    "algorithm_review_attempts",
    "algorithm_training_attempts",
]


def _ensure_legacy_user() -> str:
    conn = op.get_bind()
    legacy_id = conn.execute(
        sa.text("SELECT id FROM users WHERE email = :email"),
        {"email": "legacy@local"},
    ).scalar_one_or_none()
    if legacy_id is not None:
        return str(legacy_id)

    generated_id = str(uuid.uuid4())
    conn.execute(
        sa.text(
            """
            INSERT INTO users (
                id,
                email,
                password_hash,
                is_active,
                is_admin,
                must_change_password
            ) VALUES (
                :id,
                :email,
                :password_hash,
                :is_active,
                :is_admin,
                :must_change_password
            )
            """
        ),
        {
            "id": generated_id,
            "email": "legacy@local",
            "password_hash": "legacy-disabled",
            "is_active": False,
            "is_admin": False,
            "must_change_password": True,
        },
    )
    return generated_id


def _add_user_id_column(table_name: str) -> None:
    with op.batch_alter_table(table_name) as batch:
        batch.add_column(sa.Column("user_id", sa.Uuid(as_uuid=True), nullable=True))


def _finalize_user_id_column(table_name: str) -> None:
    with op.batch_alter_table(table_name) as batch:
        batch.create_index(f"ix_{table_name}_user_id", ["user_id"], unique=False)
        batch.create_foreign_key(
            f"fk_{table_name}_user_id_users",
            "users",
            ["user_id"],
            ["id"],
        )
        batch.alter_column("user_id", existing_type=sa.Uuid(), nullable=False)


def upgrade() -> None:
    """Add user_id to domain tables and backfill existing rows."""
    for table_name in DOMAIN_TABLES:
        _add_user_id_column(table_name)

    legacy_user_id = _ensure_legacy_user()
    conn = op.get_bind()
    for table_name in DOMAIN_TABLES:
        conn.execute(
            sa.text(f"UPDATE {table_name} SET user_id = :legacy_user_id"),
            {"legacy_user_id": legacy_user_id},
        )

    with op.batch_alter_table("algorithm_groups") as batch:
        batch.drop_constraint("uq_algorithm_groups_title_norm", type_="unique")

    for table_name in DOMAIN_TABLES:
        _finalize_user_id_column(table_name)

    with op.batch_alter_table("algorithm_groups") as batch:
        batch.create_unique_constraint(
            "uq_algorithm_groups_user_id_title_norm",
            ["user_id", "title_norm"],
        )


def downgrade() -> None:
    """Remove user_id from domain tables."""
    with op.batch_alter_table("algorithm_groups") as batch:
        batch.drop_constraint(
            "uq_algorithm_groups_user_id_title_norm",
            type_="unique",
        )

    for table_name in DOMAIN_TABLES:
        with op.batch_alter_table(table_name) as batch:
            batch.drop_constraint(f"fk_{table_name}_user_id_users", type_="foreignkey")
            batch.drop_index(f"ix_{table_name}_user_id")
            batch.drop_column("user_id")

    with op.batch_alter_table("algorithm_groups") as batch:
        batch.create_unique_constraint(
            "uq_algorithm_groups_title_norm",
            ["title_norm"],
        )
