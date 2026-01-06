"""Database session management."""

import os
from collections.abc import Iterator
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

DATABASE_URL_ENV: str = "DATABASE_URL"
DB_PATH_ENV: str = "DB_PATH"
DEFAULT_DB_PATH: str = "data/app.db"
CONTAINER_DB_PATH: str = "/data/app.db"
DOCKER_ENV_PATH: Path = Path("/.dockerenv")


def resolve_db_path() -> Path:
    """Resolve database path from environment or defaults."""
    db_path = os.getenv(DB_PATH_ENV)
    if db_path:
        return Path(db_path).expanduser()
    if DOCKER_ENV_PATH.exists():
        return Path(CONTAINER_DB_PATH)
    return Path(DEFAULT_DB_PATH)


def build_database_url() -> str:
    """Build the SQLAlchemy database URL from environment variables."""
    database_url = os.getenv(DATABASE_URL_ENV)
    if database_url:
        return database_url

    path = resolve_db_path()
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
