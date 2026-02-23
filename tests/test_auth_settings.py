"""Auth and settings tests."""

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from studying_light.db.models.user import User
from studying_light.db.models.user_settings import UserSettings


def test_register_creates_inactive_user_and_settings(
    client: TestClient,
    session: Session,
) -> None:
    """Register should create inactive user and per-user settings."""
    register_response = client.post(
        "/api/v1/auth/register",
        json={"email": "user@example.com", "password": "strongpass123"},
    )
    assert register_response.status_code == 201
    user_payload = register_response.json()
    assert user_payload["is_active"] is False
    assert user_payload["is_admin"] is False

    user = session.execute(
        select(User).where(User.email == "user@example.com")
    ).scalar_one()
    assert user is not None
    assert user.is_active is False

    settings = session.get(UserSettings, user.id)
    assert settings is not None
    assert settings.user_id == user.id


def test_login_inactive_returns_account_inactive(client: TestClient) -> None:
    """Inactive users should not be able to login."""
    register_response = client.post(
        "/api/v1/auth/register",
        json={"email": "inactive@example.com", "password": "strongpass123"},
    )
    assert register_response.status_code == 201
    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": "inactive@example.com", "password": "strongpass123"},
    )
    assert login_response.status_code == 403
    assert login_response.json()["code"] == "ACCOUNT_INACTIVE"
