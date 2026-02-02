"""Add title_norm to algorithm_groups.

Revision ID: 0007_add_algorithm_group_title_norm
Revises: 0006_add_algorithms_tables
Create Date: 2026-02-02 00:00:00.000000
"""

import sqlalchemy as sa

from alembic import op

revision = "0007_add_algorithm_group_title_norm"
down_revision = "0006_add_algorithms_tables"
branch_labels = None
depends_on = None


def _dedupe_algorithm_groups(conn: sa.engine.Connection) -> None:
    rows = conn.execute(
        sa.text(
            """
            SELECT title_norm, MIN(id) AS keep_id
            FROM algorithm_groups
            GROUP BY title_norm
            HAVING COUNT(*) > 1
            """
        )
    ).fetchall()

    for row in rows:
        title_norm = row.title_norm
        keep_id = row.keep_id
        dup_ids = [
            dup.id
            for dup in conn.execute(
                sa.text(
                    """
                    SELECT id
                    FROM algorithm_groups
                    WHERE title_norm = :title_norm AND id != :keep_id
                    """
                ),
                {"title_norm": title_norm, "keep_id": keep_id},
            ).fetchall()
        ]
        if not dup_ids:
            continue

        conn.execute(
            sa.text(
                "UPDATE algorithms SET group_id = :keep_id WHERE group_id IN :dup_ids"
            ).bindparams(sa.bindparam("dup_ids", expanding=True)),
            {"keep_id": keep_id, "dup_ids": dup_ids},
        )
        conn.execute(
            sa.text("DELETE FROM algorithm_groups WHERE id IN :dup_ids").bindparams(
                sa.bindparam("dup_ids", expanding=True)
            ),
            {"dup_ids": dup_ids},
        )


def upgrade() -> None:
    """Add normalized group title and unique constraint."""
    with op.batch_alter_table("algorithm_groups") as batch:
        batch.add_column(sa.Column("title_norm", sa.Text(), nullable=True))

    op.execute(sa.text("UPDATE algorithm_groups SET title_norm = lower(trim(title))"))

    conn = op.get_bind()
    _dedupe_algorithm_groups(conn)

    with op.batch_alter_table("algorithm_groups") as batch:
        batch.alter_column("title_norm", nullable=False)
        batch.create_unique_constraint(
            "uq_algorithm_groups_title_norm",
            ["title_norm"],
        )


def downgrade() -> None:
    """Drop normalized group title and unique constraint."""
    with op.batch_alter_table("algorithm_groups") as batch:
        batch.drop_constraint("uq_algorithm_groups_title_norm", type_="unique")
        batch.drop_column("title_norm")
