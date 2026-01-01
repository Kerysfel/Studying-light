"""Test fixtures for API tests."""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import studying_light.db.models  # noqa: F401
from studying_light.db.base import Base
from studying_light.db.session import get_session
from studying_light.main import app


@pytest.fixture()
def session() -> Iterator[Session]:
    """Provide a transactional database session for tests."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_local = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    db = session_local()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture()
def client(session: Session) -> Iterator[TestClient]:
    """Provide a test client with an overridden database session."""

    def _get_session() -> Iterator[Session]:
        yield session

    app.dependency_overrides[get_session] = _get_session
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
