"""Alembic environment configuration."""

from logging.config import fileConfig

import sqlalchemy as sa
from sqlalchemy import MetaData, engine_from_config, pool

from alembic import context
from studying_light.db.session import build_database_url

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)


config.set_main_option("sqlalchemy.url", build_database_url())

target_metadata: MetaData | None = None
try:
    import studying_light.db.models as models
    from studying_light.db.base import Base

    target_metadata = Base.metadata
    _ = models
except ModuleNotFoundError:
    target_metadata = None


def run_migrations_offline() -> None:
    """Run migrations without a database connection."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations with a database connection."""
    section = config.get_section(config.config_ini_section, {})
    url = config.get_main_option("sqlalchemy.url") or build_database_url()
    section["sqlalchemy.url"] = url
    connectable = engine_from_config(
        section,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.begin() as connection:
        version_table = sa.Table(
            "alembic_version",
            sa.MetaData(),
            sa.Column("version_num", sa.String(64), primary_key=True),
        )
        version_table.create(connection, checkfirst=True)
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )

        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
