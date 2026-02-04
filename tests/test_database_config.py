"""Tests for database configuration."""

from pathlib import Path


def test_build_database_url_uses_database_url(monkeypatch) -> None:
    """DATABASE_URL should override DB_PATH."""
    url = "postgresql+psycopg://studying_light:studying_light@localhost:5432/studying_light"
    monkeypatch.setenv("DATABASE_URL", url)
    monkeypatch.delenv("DB_PATH", raising=False)

    from studying_light.db import session as session_module

    assert session_module.build_database_url() == url


def test_build_database_url_falls_back_to_db_path(monkeypatch, tmp_path) -> None:
    """DB_PATH should be used when DATABASE_URL is not set."""
    db_path = tmp_path / "app.db"
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("DB_PATH", str(db_path))

    from studying_light.db import session as session_module

    expected = f"sqlite:///{Path(db_path).resolve().as_posix()}"
    assert session_module.build_database_url() == expected
