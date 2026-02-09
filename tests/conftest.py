"""Test fixtures for API tests."""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import studying_light.db.models  # noqa: F401
from studying_light.db.base import Base
from studying_light.db.models.user import User
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


def _register_and_login(
    client: TestClient,
    session: Session,
    *,
    email: str,
    password: str = "strongpass123",
) -> dict[str, str]:
    register_response = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password},
    )
    assert register_response.status_code == 201
    user = session.execute(select(User).where(User.email == email)).scalar_one()
    user.is_active = True
    session.commit()

    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def auth_headers(client: TestClient, session: Session) -> dict[str, str]:
    """Default authenticated user headers."""
    return _register_and_login(client, session, email="user@local")


@pytest.fixture()
def user_pair_headers(
    client: TestClient,
    session: Session,
) -> tuple[dict[str, str], dict[str, str]]:
    """Headers for two distinct users."""
    first = _register_and_login(client, session, email="user-a@local")
    second = _register_and_login(client, session, email="user-b@local")
    return first, second
