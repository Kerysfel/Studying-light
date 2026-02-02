"""Algorithm training API tests."""

from datetime import date


def _import_algorithm(client, group_id: int) -> int:
    payload = {
        "groups": [],
        "algorithms": [
            {
                "title": "BFS",
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
            }
        ],
    }
    response = client.post("/api/v1/algorithms/import", json=payload)
    assert response.status_code == 201
    return response.json()["algorithms_created"][0]["algorithm_id"]


def test_algorithm_training_attempts(client) -> None:
    group_response = client.post(
        "/api/v1/algorithm-groups",
        json={"title": "Graphs"},
    )
    assert group_response.status_code == 201
    group_id = group_response.json()["id"]

    algorithm_id = _import_algorithm(client, group_id)

    gpt_payload = {
        "meta": {
            "group_title": "Graphs",
            "algorithm_title": "BFS",
            "interval_days": None,
            "review_date": date.today().isoformat(),
        },
        "overall": {
            "rating_1_to_5": 4,
            "key_gaps": [],
            "next_steps": [],
            "limitations": [],
        },
        "items": [
            {
                "question": "Q",
                "user_answer": "A",
                "rating_1_to_5": 4,
                "is_answered": True,
                "mistakes": [],
                "short_feedback": "Ok",
                "correct_answer": "Answer",
            }
        ],
    }

    create_response = client.post(
        "/api/v1/algorithm-trainings",
        json={
            "algorithm_id": algorithm_id,
            "code_text": "attempt",
            "mode": "memory",
            "gpt_check_result": gpt_payload,
        },
    )
    assert create_response.status_code == 201
    created = create_response.json()
    assert created["algorithm_id"] == algorithm_id
    assert created["mode"] == "memory"
    assert created["rating_1_to_5"] == 4
    assert created["gpt_check_json"] is not None

    list_response = client.get(
        "/api/v1/algorithm-trainings",
        params={"algorithm_id": algorithm_id},
    )
    assert list_response.status_code == 200
    items = list_response.json()
    assert len(items) == 1
    assert items[0]["id"] == created["id"]

    typing_response = client.post(
        "/api/v1/algorithm-trainings",
        json={
            "algorithm_id": algorithm_id,
            "code_text": "typed",
            "mode": "typing",
            "accuracy": 92.5,
            "duration_sec": 45,
        },
    )
    assert typing_response.status_code == 201
    typing_payload = typing_response.json()
    assert typing_payload["mode"] == "typing"
    assert typing_payload["accuracy"] == 92.5
    assert typing_payload["duration_sec"] == 45
