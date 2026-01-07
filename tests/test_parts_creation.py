"""Reading part creation tests."""

from fastapi.testclient import TestClient


def test_create_part_computes_pages_read(client: TestClient) -> None:
    """Ensure page_end computes pages_read based on the last saved page."""
    book_response = client.post("/api/v1/books", json={"title": "Test Book"})
    assert book_response.status_code == 201
    book_id = book_response.json()["id"]

    first_response = client.post(
        "/api/v1/parts",
        json={"book_id": book_id, "page_end": 10},
    )
    assert first_response.status_code == 201
    first_part = first_response.json()
    assert first_part["page_end"] == 10
    assert first_part["pages_read"] == 10

    second_response = client.post(
        "/api/v1/parts",
        json={"book_id": book_id, "page_end": 25},
    )
    assert second_response.status_code == 201
    second_part = second_response.json()
    assert second_part["page_end"] == 25
    assert second_part["pages_read"] == 15
