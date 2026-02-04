"""Auth and settings tests."""

from fastapi.testclient import TestClient


def test_register_login_settings(client: TestClient) -> None:
    """Settings should be created and accessible for the logged-in user."""
    register_response = client.post(
        "/api/v1/auth/register",
        json={"email": "user@example.com", "password": "secret"},
    )
    assert register_response.status_code == 201
    user_id = register_response.json()["id"]

    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": "user@example.com", "password": "secret"},
    )
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]

    settings_response = client.get(
        "/api/v1/settings",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert settings_response.status_code == 200
    settings = settings_response.json()
    assert settings["user_id"] == user_id
