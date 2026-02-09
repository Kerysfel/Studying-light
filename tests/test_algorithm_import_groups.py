"""Tests for algorithm group handling during import."""

from sqlalchemy import func, select

from studying_light.db.models.algorithm_group import AlgorithmGroup


def _build_payload(
    *,
    algorithm_title: str,
    group_id: int | None = None,
    group_title_new: str | None = None,
) -> dict:
    return {
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
                "group_title_new": group_title_new,
            }
        ],
    }


def test_import_with_existing_group_id(client, auth_headers: dict[str, str]) -> None:
    group_response = client.post(
        "/api/v1/algorithm-groups",
        json={"title": "Graphs"},
        headers=auth_headers,
    )
    assert group_response.status_code == 201
    group_id = group_response.json()["id"]

    payload = _build_payload(algorithm_title="BFS", group_id=group_id)
    response = client.post(
        "/api/v1/algorithms/import",
        json=payload,
        headers=auth_headers,
    )
    assert response.status_code == 201
    response_payload = response.json()
    assert response_payload["groups_created"] == 0
    assert response_payload["algorithms_created"][0]["group_id"] == group_id


def test_import_with_new_title_reuses_group(
    client,
    session,
    auth_headers: dict[str, str],
) -> None:
    first_payload = _build_payload(
        algorithm_title="BFS",
        group_title_new="  Graphs  ",
    )
    first_response = client.post(
        "/api/v1/algorithms/import",
        json=first_payload,
        headers=auth_headers,
    )
    assert first_response.status_code == 201
    assert first_response.json()["groups_created"] == 1

    second_payload = _build_payload(
        algorithm_title="DFS",
        group_title_new="graphs",
    )
    second_response = client.post(
        "/api/v1/algorithms/import",
        json=second_payload,
        headers=auth_headers,
    )
    assert second_response.status_code == 201
    assert second_response.json()["groups_created"] == 0

    group_count = session.execute(select(func.count(AlgorithmGroup.id))).scalar_one()
    assert group_count == 1
