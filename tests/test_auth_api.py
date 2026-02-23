"""Authentication API tests."""

from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from studying_light.db.models.password_reset_request import PasswordResetRequest
from studying_light.db.models.user import User
from studying_light.security import hash_password
from studying_light.services.user_settings import build_default_settings


def _create_user(
    session: Session,
    *,
    email: str,
    password: str,
    is_active: bool,
    is_admin: bool = False,
) -> User:
    user = User(
        email=email,
        password_hash=hash_password(password),
        is_active=is_active,
        is_admin=is_admin,
    )
    session.add(user)
    session.flush()
    session.add(build_default_settings(user.id))
    session.commit()
    session.refresh(user)
    return user


def test_admin_user_can_login(client, session: Session) -> None:
    """Active admin user should be able to login."""
    _create_user(
        session,
        email="admin@example.com",
        password="adminpass123",
        is_active=True,
        is_admin=True,
    )

    response = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "adminpass123"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["token_type"] == "bearer"
    assert payload["access_token"]


def test_request_password_reset_always_ok_and_records_existing_user(
    client,
    session: Session,
) -> None:
    """Password reset request should not reveal user existence."""
    _create_user(
        session,
        email="known@example.com",
        password="knownpass123",
        is_active=True,
    )

    before_count = session.execute(
        select(func.count(PasswordResetRequest.id))
    ).scalar_one()

    existing_response = client.post(
        "/api/v1/auth/request-password-reset",
        json={"email": "known@example.com"},
    )
    assert existing_response.status_code == 200
    assert existing_response.json() == {"status": "ok"}

    after_existing = session.execute(
        select(func.count(PasswordResetRequest.id))
    ).scalar_one()
    assert after_existing == before_count + 1

    missing_response = client.post(
        "/api/v1/auth/request-password-reset",
        json={"email": "missing@example.com"},
    )
    assert missing_response.status_code == 200
    assert missing_response.json() == {"status": "ok"}

    after_missing = session.execute(
        select(func.count(PasswordResetRequest.id))
    ).scalar_one()
    assert after_missing == after_existing


def test_temp_password_login_and_change_password_flow(
    client,
    session: Session,
) -> None:
    """Temp password login should force password change and invalidate temp password."""
    user = _create_user(
        session,
        email="temp@example.com",
        password="regularpass123",
        is_active=True,
    )
    user.temp_password_hash = hash_password("temppass123")
    user.temp_password_expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
    user.temp_password_used_at = None
    user.must_change_password = False
    session.commit()

    temp_login = client.post(
        "/api/v1/auth/login",
        json={"email": "temp@example.com", "password": "temppass123"},
    )
    assert temp_login.status_code == 200
    token = temp_login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    me_after_temp = client.get("/api/v1/auth/me", headers=headers)
    assert me_after_temp.status_code == 200
    assert me_after_temp.json()["must_change_password"] is True

    change_password = client.post(
        "/api/v1/auth/change-password",
        json={
            "current_password": "temppass123",
            "new_password": "newpass12345",
        },
        headers=headers,
    )
    assert change_password.status_code == 200
    assert change_password.json() == {"status": "ok"}

    me_after_change = client.get("/api/v1/auth/me", headers=headers)
    assert me_after_change.status_code == 200
    assert me_after_change.json()["must_change_password"] is False

    temp_login_again = client.post(
        "/api/v1/auth/login",
        json={"email": "temp@example.com", "password": "temppass123"},
    )
    assert temp_login_again.status_code == 401
    assert temp_login_again.json()["code"] == "AUTH_INVALID"

    new_login = client.post(
        "/api/v1/auth/login",
        json={"email": "temp@example.com", "password": "newpass12345"},
    )
    assert new_login.status_code == 200


def test_api_requires_token(client) -> None:
    """Domain endpoints must reject anonymous requests."""
    response = client.get("/api/v1/books")
    assert response.status_code == 401
    payload = response.json()
    assert payload["code"] == "AUTH_REQUIRED"
