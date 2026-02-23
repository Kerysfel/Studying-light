"""Algorithm group and algorithm management API tests."""

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from studying_light.db.models.algorithm import Algorithm


def _create_book_and_part(client: TestClient, headers: dict[str, str]) -> int:
    book_response = client.post(
        "/api/v1/books",
        json={"title": "Test Book"},
        headers=headers,
    )
    assert book_response.status_code == 201
    book_id = book_response.json()["id"]

    part_payload = {
        "book_id": book_id,
        "label": "Part 1",
    }
    part_response = client.post("/api/v1/parts", json=part_payload, headers=headers)
    assert part_response.status_code == 201
    return part_response.json()["id"]


def _import_algorithm(
    client: TestClient,
    headers: dict[str, str],
    *,
    group_id: int,
    algorithm_title: str,
    source_part_id: int,
) -> None:
    payload = {
        "groups": [],
        "algorithms": [
            {
                "title": algorithm_title,
                "summary": "Summary",
                "when_to_use": "When to use",
                "complexity": "O(1)",
                "invariants": ["Always holds"],
                "steps": ["Step 1"],
                "corner_cases": ["None"],
                "review_questions_by_interval": {
                    1: ["Q1"],
                    7: ["Q2"],
                    16: ["Q3"],
                    35: ["Q4"],
                    90: ["Q5"],
                },
                "code": {
                    "code_kind": "pseudocode",
                    "language": "text",
                    "code_text": "code",
                },
                "group_id": group_id,
                "source_part_id": source_part_id,
            }
        ],
    }
    response = client.post("/api/v1/algorithms/import", json=payload, headers=headers)
    assert response.status_code == 201


def test_algorithm_group_list_and_detail(
    client: TestClient,
    session: Session,
    auth_headers: dict[str, str],
) -> None:
    group_response = client.post(
        "/api/v1/algorithm-groups",
        json={
            "title": "Graphs",
            "description": "Graph algorithms",
            "notes": "Core topics",
        },
        headers=auth_headers,
    )
    assert group_response.status_code == 201
    group_id = group_response.json()["id"]

    part_id = _create_book_and_part(client, auth_headers)
    _import_algorithm(
        client,
        auth_headers,
        group_id=group_id,
        algorithm_title="BFS",
        source_part_id=part_id,
    )

    list_response = client.get(
        "/api/v1/algorithm-groups",
        params={"query": "graph"},
        headers=auth_headers,
    )
    assert list_response.status_code == 200
    list_payload = list_response.json()
    assert len(list_payload) == 1
    assert list_payload[0]["title"] == "Graphs"
    assert list_payload[0]["algorithms_count"] == 1

    detail_response = client.get(
        f"/api/v1/algorithm-groups/{group_id}",
        headers=auth_headers,
    )
    assert detail_response.status_code == 200
    detail_payload = detail_response.json()
    assert detail_payload["title"] == "Graphs"
    assert detail_payload["algorithms_count"] == 1
    assert detail_payload["algorithms"][0]["title"] == "BFS"


def test_algorithm_list_and_detail(
    client: TestClient,
    session: Session,
    auth_headers: dict[str, str],
) -> None:
    group_response = client.post(
        "/api/v1/algorithm-groups",
        json={
            "title": "Trees",
            "description": "Tree algorithms",
            "notes": "Traversal",
        },
        headers=auth_headers,
    )
    assert group_response.status_code == 201
    group_id = group_response.json()["id"]

    part_id = _create_book_and_part(client, auth_headers)
    _import_algorithm(
        client,
        auth_headers,
        group_id=group_id,
        algorithm_title="DFS",
        source_part_id=part_id,
    )

    algorithm = session.execute(
        select(Algorithm).where(Algorithm.title == "DFS")
    ).scalar_one()

    list_response = client.get(
        "/api/v1/algorithms",
        params={"group_id": group_id},
        headers=auth_headers,
    )
    assert list_response.status_code == 200
    list_payload = list_response.json()
    assert len(list_payload) == 1
    assert list_payload[0]["group_title"] == "Trees"
    assert list_payload[0]["review_items_count"] == 5

    detail_response = client.get(
        f"/api/v1/algorithms/{algorithm.id}",
        headers=auth_headers,
    )
    assert detail_response.status_code == 200
    detail_payload = detail_response.json()
    assert detail_payload["group_title"] == "Trees"
    assert detail_payload["review_items_count"] == 5
    assert detail_payload["code_snippets"][0]["code_kind"] == "pseudocode"
    assert detail_payload["source_part"]["id"] == part_id
