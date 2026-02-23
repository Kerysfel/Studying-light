"""Tests for database configuration."""

from pathlib import Path

import pytest


def test_build_database_url_uses_database_url(monkeypatch) -> None:
    """DATABASE_URL should override DB_PATH."""
    url = "postgresql+psycopg://studying_light:studying_light@localhost:5432/studying_light"
    monkeypatch.setenv("DATABASE_URL", url)
    monkeypatch.delenv("DB_PATH", raising=False)
    monkeypatch.delenv("IN_DOCKER", raising=False)

    from studying_light.db import session as session_module

    assert session_module.build_database_url() == url


def test_build_database_url_falls_back_to_db_path(monkeypatch, tmp_path) -> None:
    """Local environment should allow SQLite fallback when DATABASE_URL is absent."""
    db_path = tmp_path / "app.db"
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("APP_ENV", "local")
    monkeypatch.delenv("IN_DOCKER", raising=False)
    monkeypatch.setenv("DB_PATH", str(db_path))

    from studying_light.db import session as session_module

    expected = f"sqlite:///{Path(db_path).resolve().as_posix()}"
    assert session_module.build_database_url() == expected


def test_build_database_url_requires_database_url_in_docker(monkeypatch) -> None:
    """Docker mode without DATABASE_URL must fail with structured config error."""
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("IN_DOCKER", "1")
    monkeypatch.setenv("APP_ENV", "docker")

    from studying_light.db import session as session_module

    with pytest.raises(session_module.DatabaseConfigError) as exc_info:
        session_module.build_database_url()

    assert exc_info.value.payload == {
        "detail": "DATABASE_URL is required when running in Docker",
        "code": "DATABASE_URL_REQUIRED",
    }
