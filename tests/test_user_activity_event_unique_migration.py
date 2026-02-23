"""Migration tests for user_activity_events natural-key uniqueness."""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import pytest
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError

from alembic import command


def _build_alembic_config() -> Config:
    return Config("alembic.ini")


def _insert_user(connection, *, user_id: str, email: str) -> None:
    connection.execute(
        text(
            """
            INSERT INTO users (id, email, password_hash)
            VALUES (:id, :email, :password_hash)
            """
        ),
        {
            "id": user_id,
            "email": email,
            "password_hash": "hash",
        },
    )


def _insert_reading_event(connection, *, user_id: str, reading_part_id: int) -> None:
    connection.execute(
        text(
            """
            INSERT INTO user_activity_events (user_id, activity_kind, reading_part_id)
            VALUES (:user_id, 'reading_session', :reading_part_id)
            """
        ),
        {
            "user_id": user_id,
            "reading_part_id": reading_part_id,
        },
    )


def test_unique_ref_migration_cleans_and_enforces_uniqueness(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Migration 0016 should cleanup duplicate refs and enforce unique indexes."""
    db_path = tmp_path / "migration-user-activity.db"
    db_url = f"sqlite:///{db_path}"
    monkeypatch.setenv("DATABASE_URL", db_url)
    alembic_cfg = _build_alembic_config()

    command.upgrade(alembic_cfg, "0015_add_user_activity_events")
    engine = create_engine(db_url)

    user_id = str(uuid4())
    with engine.begin() as connection:
        _insert_user(connection, user_id=user_id, email="migration@local")
        _insert_reading_event(connection, user_id=user_id, reading_part_id=11)
        _insert_reading_event(connection, user_id=user_id, reading_part_id=11)

    with engine.connect() as connection:
        duplicates_before = connection.execute(
            text(
                """
                SELECT COUNT(*) FROM user_activity_events
                WHERE activity_kind = 'reading_session' AND reading_part_id = 11
                """
            )
        ).scalar_one()
    assert duplicates_before == 2

    command.upgrade(alembic_cfg, "0016_add_user_activity_event_unique_refs")
    with engine.connect() as connection:
        duplicates_after_cleanup = connection.execute(
            text(
                """
                SELECT COUNT(*) FROM user_activity_events
                WHERE activity_kind = 'reading_session' AND reading_part_id = 11
                """
            )
        ).scalar_one()
    assert duplicates_after_cleanup == 1

    with pytest.raises(IntegrityError):
        with engine.begin() as connection:
            _insert_reading_event(connection, user_id=user_id, reading_part_id=11)

    command.downgrade(alembic_cfg, "0015_add_user_activity_events")
    with engine.begin() as connection:
        _insert_reading_event(connection, user_id=user_id, reading_part_id=11)

    with engine.connect() as connection:
        duplicates_after_downgrade = connection.execute(
            text(
                """
                SELECT COUNT(*) FROM user_activity_events
                WHERE activity_kind = 'reading_session' AND reading_part_id = 11
                """
            )
        ).scalar_one()
    assert duplicates_after_downgrade == 2

    engine.dispose()
