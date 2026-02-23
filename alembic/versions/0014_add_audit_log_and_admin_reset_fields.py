"""Add audit log and password reset processing fields.

Revision ID: 0014_add_audit_log_and_admin_reset_fields
Revises: 0013_add_password_reset_requests
Create Date: 2026-02-10 00:00:00.000000
"""

import sqlalchemy as sa

from alembic import op

revision = "0014_add_audit_log_and_admin_reset_fields"
down_revision = "0013_add_password_reset_requests"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add audit log table and reset processing fields."""
    op.create_table(
        "audit_log",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "actor_user_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column(
            "target_user_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("payload_json", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )
    op.create_index("ix_audit_log_actor_user_id", "audit_log", ["actor_user_id"], unique=False)
    op.create_index("ix_audit_log_target_user_id", "audit_log", ["target_user_id"], unique=False)

    with op.batch_alter_table("password_reset_requests") as batch:
        batch.add_column(
            sa.Column(
                "requested_at",
                sa.DateTime(timezone=True),
                nullable=True,
            )
        )
        batch.add_column(sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True))
        batch.add_column(sa.Column("processed_by_admin_id", sa.Uuid(as_uuid=True), nullable=True))
        batch.create_index(
            "ix_password_reset_requests_processed_by_admin_id",
            ["processed_by_admin_id"],
            unique=False,
        )
        batch.create_foreign_key(
            "fk_password_reset_requests_processed_by_admin_id_users",
            "users",
            ["processed_by_admin_id"],
            ["id"],
            ondelete="SET NULL",
        )

    connection = op.get_bind()
    connection.execute(
        sa.text(
            """
            UPDATE password_reset_requests
            SET requested_at = created_at
            WHERE requested_at IS NULL
            """
        )
    )

    with op.batch_alter_table("password_reset_requests") as batch:
        batch.alter_column(
            "requested_at",
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        )


def downgrade() -> None:
    """Revert audit log and reset processing fields."""
    with op.batch_alter_table("password_reset_requests") as batch:
        batch.drop_constraint(
            "fk_password_reset_requests_processed_by_admin_id_users",
            type_="foreignkey",
        )
        batch.drop_index("ix_password_reset_requests_processed_by_admin_id")
        batch.drop_column("processed_by_admin_id")
        batch.drop_column("processed_at")
        batch.drop_column("requested_at")

    op.drop_index("ix_audit_log_target_user_id", table_name="audit_log")
    op.drop_index("ix_audit_log_actor_user_id", table_name="audit_log")
    op.drop_table("audit_log")
