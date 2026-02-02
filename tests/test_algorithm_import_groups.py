"""Tests for algorithm group normalization during import."""

from sqlalchemy import func, select

from studying_light.db.models.algorithm_group import AlgorithmGroup


def _build_payload(group_title: str, algorithm_title: str) -> dict:
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
                "group_title": group_title,
            }
        ],
    }


def test_import_reuses_algorithm_group(client, session) -> None:
    first_payload = _build_payload("  Graphs  ", "BFS")
    first_response = client.post("/algorithms/import", json=first_payload)
    assert first_response.status_code == 201
    assert first_response.json()["groups_created"] == 1

    second_payload = _build_payload("graphs", "DFS")
    second_response = client.post("/algorithms/import", json=second_payload)
    assert second_response.status_code == 201
    assert second_response.json()["groups_created"] == 0

    group_count = session.execute(select(func.count(AlgorithmGroup.id))).scalar_one()
    assert group_count == 1
