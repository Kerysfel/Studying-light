"""Database session management."""

import json
import os
from collections.abc import Iterator
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

DATABASE_URL_ENV: str = "DATABASE_URL"
DB_PATH_ENV: str = "DB_PATH"
APP_ENV_ENV: str = "APP_ENV"
IN_DOCKER_ENV: str = "IN_DOCKER"
LOCAL_ENV: str = "local"
DEFAULT_DB_PATH: str = "data/app.db"
DOCKER_ENV_PATH: Path = Path("/.dockerenv")


class DatabaseConfigError(RuntimeError):
    """Raised when database environment variables are invalid."""

    def __init__(
        self,
        *,
        detail: str,
        code: str,
        errors: list[dict[str, object]] | None = None,
    ) -> None:
        self.payload: dict[str, object] = {"detail": detail, "code": code}
        if errors:
            self.payload["errors"] = errors
        super().__init__(json.dumps(self.payload, ensure_ascii=False))


def _is_docker_runtime() -> bool:
    return os.getenv(IN_DOCKER_ENV) == "1" or DOCKER_ENV_PATH.exists()


def build_database_url() -> str:
    """Build the SQLAlchemy database URL from environment variables."""
    database_url = (os.getenv(DATABASE_URL_ENV) or "").strip()
    if database_url:
        return database_url

    if _is_docker_runtime():
        raise DatabaseConfigError(
            detail="DATABASE_URL is required when running in Docker",
            code="DATABASE_URL_REQUIRED",
        )

    app_env = (os.getenv(APP_ENV_ENV) or LOCAL_ENV).strip().lower()
    if app_env != LOCAL_ENV:
        raise DatabaseConfigError(
            detail="DATABASE_URL is required outside local environment",
            code="DATABASE_URL_REQUIRED",
        )

    db_path = os.getenv(DB_PATH_ENV, DEFAULT_DB_PATH)
    path = Path(db_path).expanduser()
    if not path.is_absolute():
        path = path.resolve()
    return f"sqlite:///{path.as_posix()}"


database_url = build_database_url()
connect_args = {}
if database_url.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(database_url, connect_args=connect_args)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_session() -> Iterator[Session]:
    """Provide a database session."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
