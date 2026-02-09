"""Multi-user data isolation tests."""

from fastapi.testclient import TestClient


def _register_and_login(
    client: TestClient,
    *,
    email: str,
    password: str = "secret",
) -> dict[str, str]:
    register = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password},
    )
    assert register.status_code == 201
    login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_multi_user_isolation_books_parts_reviews_algorithms(
    client: TestClient,
) -> None:
    """User B must not access or mutate user A domain data."""
    user_a_headers = _register_and_login(client, email="isolation-a@local")
    user_b_headers = _register_and_login(client, email="isolation-b@local")

    create_book = client.post(
        "/api/v1/books",
        json={"title": "A Book"},
        headers=user_a_headers,
    )
    assert create_book.status_code == 201
    book_id = create_book.json()["id"]

    create_part = client.post(
        "/api/v1/parts",
        json={"book_id": book_id, "label": "A Part"},
        headers=user_a_headers,
    )
    assert create_part.status_code == 201
    part_id = create_part.json()["id"]

    import_response = client.post(
        f"/api/v1/parts/{part_id}/import_gpt",
        json={
            "gpt_summary": "Summary",
            "gpt_questions_by_interval": {
                "1": ["Q1"],
                "7": ["Q2"],
                "16": ["Q3"],
                "35": ["Q4"],
                "90": ["Q5"],
            },
        },
        headers=user_a_headers,
    )
    assert import_response.status_code == 200
    review_id = import_response.json()["review_items"][0]["id"]

    create_group = client.post(
        "/api/v1/algorithm-groups",
        json={"title": "A Group"},
        headers=user_a_headers,
    )
    assert create_group.status_code == 201
    group_id = create_group.json()["id"]

    import_algorithm = client.post(
        "/api/v1/algorithms/import",
        json={
            "groups": [],
            "algorithms": [
                {
                    "title": "Algo A",
                    "summary": "Summary",
                    "when_to_use": "Use",
                    "complexity": "O(1)",
                    "invariants": ["inv"],
                    "steps": ["step"],
                    "corner_cases": ["case"],
                    "review_questions_by_interval": {
                        "1": ["Q1"],
                        "7": ["Q2"],
                        "16": ["Q3"],
                        "35": ["Q4"],
                        "90": ["Q5"],
                    },
                    "code": {
                        "code_kind": "pseudocode",
                        "language": "text",
                        "code_text": "code",
                    },
                    "group_id": group_id,
                    "source_part_id": part_id,
                }
            ],
        },
        headers=user_a_headers,
    )
    assert import_algorithm.status_code == 201
    algorithm_id = import_algorithm.json()["algorithms_created"][0]["algorithm_id"]

    list_books_b = client.get("/api/v1/books", headers=user_b_headers)
    assert list_books_b.status_code == 200
    assert list_books_b.json() == []

    update_book_b = client.patch(
        f"/api/v1/books/{book_id}",
        json={"title": "Hack"},
        headers=user_b_headers,
    )
    assert update_book_b.status_code == 404

    delete_book_b = client.delete(f"/api/v1/books/{book_id}", headers=user_b_headers)
    assert delete_book_b.status_code == 404

    list_parts_b = client.get(
        "/api/v1/parts",
        params={"book_id": book_id},
        headers=user_b_headers,
    )
    assert list_parts_b.status_code == 200
    assert list_parts_b.json() == []

    import_part_b = client.post(
        f"/api/v1/parts/{part_id}/import_gpt",
        json={
            "gpt_summary": "Nope",
            "gpt_questions_by_interval": {
                "1": ["Q1"],
                "7": ["Q2"],
                "16": ["Q3"],
                "35": ["Q4"],
                "90": ["Q5"],
            },
        },
        headers=user_b_headers,
    )
    assert import_part_b.status_code == 404

    review_detail_b = client.get(f"/api/v1/reviews/{review_id}", headers=user_b_headers)
    assert review_detail_b.status_code == 404

    review_complete_b = client.post(
        f"/api/v1/reviews/{review_id}/complete",
        json={"answers": {"q": "A"}},
        headers=user_b_headers,
    )
    assert review_complete_b.status_code == 404

    groups_list_b = client.get("/api/v1/algorithm-groups", headers=user_b_headers)
    assert groups_list_b.status_code == 200
    assert groups_list_b.json() == []

    group_detail_b = client.get(
        f"/api/v1/algorithm-groups/{group_id}",
        headers=user_b_headers,
    )
    assert group_detail_b.status_code == 404

    algorithms_list_b = client.get(
        "/api/v1/algorithms",
        params={"group_id": group_id},
        headers=user_b_headers,
    )
    assert algorithms_list_b.status_code == 404

    algorithm_detail_b = client.get(
        f"/api/v1/algorithms/{algorithm_id}",
        headers=user_b_headers,
    )
    assert algorithm_detail_b.status_code == 404

    trainings_b = client.get(
        "/api/v1/algorithm-trainings",
        params={"algorithm_id": algorithm_id},
        headers=user_b_headers,
    )
    assert trainings_b.status_code == 200
    assert trainings_b.json() == []

    reviews_today_a = client.get("/api/v1/reviews/today", headers=user_a_headers)
    assert reviews_today_a.status_code == 200
    assert any(item["id"] == review_id for item in reviews_today_a.json())

    reviews_today_b = client.get("/api/v1/reviews/today", headers=user_b_headers)
    assert reviews_today_b.status_code == 200
    assert all(item["id"] != review_id for item in reviews_today_b.json())

    algorithm_reviews_b = client.get(
        "/api/v1/algorithm-reviews/today",
        headers=user_b_headers,
    )
    assert algorithm_reviews_b.status_code == 200
    assert algorithm_reviews_b.json() == []

    stats_b = client.get("/api/v1/stats", headers=user_b_headers)
    assert stats_b.status_code == 200
    assert stats_b.json()["theory"]["planned_count"] == 0
    assert stats_b.json()["algorithms"]["planned_count"] == 0

    today_b = client.get("/api/v1/today", headers=user_b_headers)
    assert today_b.status_code == 200
    assert today_b.json()["active_books"] == []

    today_a = client.get("/api/v1/today", headers=user_a_headers)
    assert today_a.status_code == 200
    assert today_a.json()["active_books"][0]["id"] == book_id
