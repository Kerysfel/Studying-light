"""Book progress aggregation tests."""

from fastapi.testclient import TestClient


def test_pages_progress_uses_latest_page_end(client: TestClient) -> None:
    """Ensure progress prefers latest page_end over summed legacy pages_read."""
    register = client.post(
        "/api/v1/auth/register",
        json={"email": "pages-progress@local", "password": "secret"},
    )
    assert register.status_code == 201
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "pages-progress@local", "password": "secret"},
    )
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    book_response = client.post(
        "/api/v1/books",
        json={"title": "Test Book"},
        headers=headers,
    )
    assert book_response.status_code == 201
    book_id = book_response.json()["id"]

    legacy_part = client.post(
        "/api/v1/parts",
        json={"book_id": book_id, "pages_read": 50},
        headers=headers,
    )
    assert legacy_part.status_code == 201

    current_part = client.post(
        "/api/v1/parts",
        json={"book_id": book_id, "page_end": 61},
        headers=headers,
    )
    assert current_part.status_code == 201

    books_response = client.get("/api/v1/books", headers=headers)
    assert books_response.status_code == 200
    books = books_response.json()
    book_stats = next(item for item in books if item["id"] == book_id)
    assert book_stats["pages_read_total"] == 61

    today_response = client.get("/api/v1/today", headers=headers)
    assert today_response.status_code == 200
    today_books = today_response.json()["active_books"]
    today_book = next(item for item in today_books if item["id"] == book_id)
    assert today_book["pages_read_total"] == 61
