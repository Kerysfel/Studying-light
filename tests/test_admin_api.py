"""Admin API and heartbeat tests."""

from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from studying_light.db.models.audit_log import AuditLog
from studying_light.db.models.password_reset_request import PasswordResetRequest
from studying_light.db.models.user import User


def _register(client, email: str, password: str = "strongpass123") -> None:
    response = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password},
    )
    assert response.status_code == 201


def _parse_iso_datetime(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _activate_user(
    session: Session,
    *,
    email: str,
    is_admin: bool = False,
) -> User:
    user = session.execute(select(User).where(User.email == email)).scalar_one()
    user.is_active = True
    user.is_admin = is_admin
    session.commit()
    session.refresh(user)
    return user


def _login(client, email: str, password: str = "strongpass123") -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _admin_headers(client, session: Session) -> dict[str, str]:
    _register(client, "admin@example.com")
    _activate_user(session, email="admin@example.com", is_admin=True)
    return _login(client, "admin@example.com")


def _user_headers(client, session: Session, email: str) -> dict[str, str]:
    _register(client, email)
    _activate_user(session, email=email, is_admin=False)
    return _login(client, email)


def test_heartbeat_updates_last_seen_with_throttle(client, session: Session) -> None:
    """Heartbeat should set last_seen and respect throttle."""
    headers = _user_headers(client, session, "heartbeat-user@example.com")

    user = session.execute(
        select(User).where(User.email == "heartbeat-user@example.com")
    ).scalar_one()
    user.last_seen_at = None
    session.commit()

    first = client.post("/api/v1/me/heartbeat", headers=headers)
    assert first.status_code == 200
    assert first.json() == {"status": "ok"}

    session.refresh(user)
    first_seen = user.last_seen_at
    assert first_seen is not None

    second = client.post("/api/v1/me/heartbeat", headers=headers)
    assert second.status_code == 200
    assert second.json() == {"status": "ok"}

    session.refresh(user)
    assert user.last_seen_at == first_seen


def test_non_admin_cannot_access_admin_routes(
    client,
    session: Session,
) -> None:
    """Non-admin should receive FORBIDDEN on admin endpoints."""
    headers = _user_headers(client, session, "regular-user@example.com")

    response = client.get("/api/v1/admin/users", headers=headers)
    assert response.status_code == 403
    assert response.json()["code"] == "FORBIDDEN"


def test_admin_can_activate_and_deactivate_users_with_audit(
    client,
    session: Session,
) -> None:
    """Admin activation actions should be persisted and audited."""
    admin_headers = _admin_headers(client, session)

    _register(client, "target-user@example.com")
    target_user = session.execute(
        select(User).where(User.email == "target-user@example.com")
    ).scalar_one()
    assert target_user.is_active is False

    activate_response = client.patch(
        f"/api/v1/admin/users/{target_user.id}/activate",
        headers=admin_headers,
    )
    assert activate_response.status_code == 200
    assert activate_response.json()["is_active"] is True

    deactivate_response = client.patch(
        f"/api/v1/admin/users/{target_user.id}/deactivate",
        headers=admin_headers,
    )
    assert deactivate_response.status_code == 200
    assert deactivate_response.json()["is_active"] is False

    actions = session.execute(
        select(AuditLog.action)
        .where(AuditLog.target_user_id == target_user.id)
        .order_by(AuditLog.created_at)
    ).scalars().all()
    assert actions == ["USER_ACTIVATED", "USER_DEACTIVATED"]


def test_admin_password_reset_flow_with_temp_password(
    client,
    session: Session,
) -> None:
    """Admin should process reset request and issue usable temp password."""
    admin_headers = _admin_headers(client, session)
    _register(client, "reset-user@example.com")

    user = session.execute(
        select(User).where(User.email == "reset-user@example.com")
    ).scalar_one()
    user.is_active = True
    session.commit()

    request_reset = client.post(
        "/api/v1/auth/request-password-reset",
        json={"email": "reset-user@example.com"},
    )
    assert request_reset.status_code == 200
    assert request_reset.json() == {"status": "ok"}

    requested_list = client.get(
        "/api/v1/admin/password-resets",
        params={"status": "requested"},
        headers=admin_headers,
    )
    assert requested_list.status_code == 200
    requested_payload = requested_list.json()
    assert len(requested_payload) == 1
    request_id = requested_payload[0]["id"]

    issue_response = client.post(
        f"/api/v1/admin/password-resets/{request_id}/issue-temp-password",
        headers=admin_headers,
    )
    assert issue_response.status_code == 200
    issue_payload = issue_response.json()
    temp_password = issue_payload["temp_password"]
    assert 12 <= len(temp_password) <= 16
    expires_at = issue_payload["expires_at"]

    second_issue_response = client.post(
        f"/api/v1/admin/password-resets/{request_id}/issue-temp-password",
        headers=admin_headers,
    )
    assert second_issue_response.status_code == 409
    assert second_issue_response.json()["code"] == "RESET_ALREADY_PROCESSED"

    processed_request = session.get(PasswordResetRequest, request_id)
    assert processed_request is not None
    assert processed_request.status == "processed"
    assert processed_request.processed_at is not None
    assert processed_request.processed_by_admin_id is not None

    temp_login = client.post(
        "/api/v1/auth/login",
        json={"email": "reset-user@example.com", "password": temp_password},
    )
    assert temp_login.status_code == 200
    user_headers = {"Authorization": f"Bearer {temp_login.json()['access_token']}"}

    me_response = client.get("/api/v1/auth/me", headers=user_headers)
    assert me_response.status_code == 200
    assert me_response.json()["must_change_password"] is True

    change_response = client.post(
        "/api/v1/auth/change-password",
        json={
            "current_password": temp_password,
            "new_password": "newstrongpass456",
        },
        headers=user_headers,
    )
    assert change_response.status_code == 200
    assert change_response.json() == {"status": "ok"}

    old_temp_login = client.post(
        "/api/v1/auth/login",
        json={"email": "reset-user@example.com", "password": temp_password},
    )
    assert old_temp_login.status_code == 401
    assert old_temp_login.json()["code"] == "AUTH_INVALID"

    new_password_login = client.post(
        "/api/v1/auth/login",
        json={"email": "reset-user@example.com", "password": "newstrongpass456"},
    )
    assert new_password_login.status_code == 200

    audit_actions = session.execute(
        select(func.count(AuditLog.id)).where(
            AuditLog.action == "PASSWORD_RESET_ISSUED",
            AuditLog.target_user_id == user.id,
        )
    ).scalar_one()
    assert audit_actions == 1

    audit_entry = session.execute(
        select(AuditLog).where(
            AuditLog.action == "PASSWORD_RESET_ISSUED",
            AuditLog.target_user_id == user.id,
        )
    ).scalar_one()
    assert audit_entry.payload_json is not None
    assert audit_entry.payload_json["request_id"] == request_id
    assert audit_entry.payload_json["user_id"] == str(user.id)
    assert _parse_iso_datetime(audit_entry.payload_json["expires_at"]) == _parse_iso_datetime(expires_at)
    assert "temp_password" not in audit_entry.payload_json


def test_admin_users_list_reports_online_after_heartbeat(
    client,
    session: Session,
) -> None:
    """Admin users list should report online for recent heartbeat."""
    admin_headers = _admin_headers(client, session)
    user_headers = _user_headers(client, session, "online-user@example.com")

    user = session.execute(
        select(User).where(User.email == "online-user@example.com")
    ).scalar_one()
    user.last_seen_at = datetime.now(timezone.utc) - timedelta(minutes=20)
    session.commit()

    heartbeat = client.post("/api/v1/me/heartbeat", headers=user_headers)
    assert heartbeat.status_code == 200

    users_response = client.get(
        "/api/v1/admin/users",
        params={"query": "online-user@example.com"},
        headers=admin_headers,
    )
    assert users_response.status_code == 200
    users_payload = users_response.json()
    assert len(users_payload) == 1
    assert users_payload[0]["email"] == "online-user@example.com"
    assert users_payload[0]["online"] is True
