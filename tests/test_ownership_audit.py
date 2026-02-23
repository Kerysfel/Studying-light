"""Ownership guard regression tests for critical endpoints."""

import csv
import io
from zipfile import ZipFile

from fastapi.testclient import TestClient


def _create_book(client: TestClient, headers: dict[str, str], title: str) -> int:
    response = client.post(
        "/api/v1/books",
        json={"title": title},
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()["id"]


def _create_part(client: TestClient, headers: dict[str, str], book_id: int) -> int:
    response = client.post(
        "/api/v1/parts",
        json={"book_id": book_id, "label": "Part"},
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()["id"]


def _import_part_for_reviews(
    client: TestClient,
    headers: dict[str, str],
    part_id: int,
) -> int:
    response = client.post(
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
        headers=headers,
    )
    assert response.status_code == 200
    return response.json()["review_items"][0]["id"]


def _create_group(client: TestClient, headers: dict[str, str], title: str) -> int:
    response = client.post(
        "/api/v1/algorithm-groups",
        json={"title": title},
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()["id"]


def _algorithm_import_payload(group_id: int, source_part_id: int) -> dict:
    return {
        "groups": [],
        "algorithms": [
            {
                "title": "Algo",
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
                "source_part_id": source_part_id,
            }
        ],
    }


def _review_feedback_payload() -> dict:
    return {
        "gpt_check_result": {
            "meta": {
                "book_title": "Book",
                "part_index": 1,
                "part_label": "Part",
                "interval_days": 1,
                "review_date": "2026-02-09",
            },
            "overall": {
                "rating_1_to_5": 4,
                "score_0_to_100": 80,
                "verdict": "PASS",
                "key_gaps": [],
                "next_steps": [],
                "limitations": [],
            },
            "items": [
                {
                    "question": "Q1",
                    "user_answer": "A1",
                    "rating_1_to_5": 4,
                    "is_answered": True,
                    "mistakes": [],
                    "short_feedback": "ok",
                    "correct_answer": "A1",
                }
            ],
        }
    }


def test_parts_endpoints_require_owner(
    client: TestClient,
    user_pair_headers: tuple[dict[str, str], dict[str, str]],
) -> None:
    """POST /parts and POST /parts/{id}/import_gpt must require ownership."""
    user_a_headers, user_b_headers = user_pair_headers

    user_a_book_id = _create_book(client, user_a_headers, "A Book")
    user_a_part_id = _create_part(client, user_a_headers, user_a_book_id)

    create_for_foreign_book = client.post(
        "/api/v1/parts",
        json={"book_id": user_a_book_id, "label": "Hack"},
        headers=user_b_headers,
    )
    assert create_for_foreign_book.status_code == 404
    assert create_for_foreign_book.json()["code"] == "NOT_FOUND"

    import_foreign_part = client.post(
        f"/api/v1/parts/{user_a_part_id}/import_gpt",
        json={
            "gpt_summary": "Hack",
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
    assert import_foreign_part.status_code == 404
    assert import_foreign_part.json()["code"] == "NOT_FOUND"


def test_review_complete_and_feedback_require_owner(
    client: TestClient,
    user_pair_headers: tuple[dict[str, str], dict[str, str]],
) -> None:
    """Review completion and GPT feedback must reject foreign review ids."""
    user_a_headers, user_b_headers = user_pair_headers

    user_a_book_id = _create_book(client, user_a_headers, "A Book")
    user_a_part_id = _create_part(client, user_a_headers, user_a_book_id)
    user_a_review_id = _import_part_for_reviews(client, user_a_headers, user_a_part_id)

    complete_foreign_review = client.post(
        f"/api/v1/reviews/{user_a_review_id}/complete",
        json={"answers": {"q": "a"}},
        headers=user_b_headers,
    )
    assert complete_foreign_review.status_code == 404
    assert complete_foreign_review.json()["code"] == "NOT_FOUND"

    save_feedback_foreign_review = client.post(
        f"/api/v1/reviews/{user_a_review_id}/save_gpt_feedback",
        json=_review_feedback_payload(),
        headers=user_b_headers,
    )
    assert save_feedback_foreign_review.status_code == 404
    assert save_feedback_foreign_review.json()["code"] == "NOT_FOUND"


def test_algorithm_import_requires_owned_group_and_source_part(
    client: TestClient,
    user_pair_headers: tuple[dict[str, str], dict[str, str]],
) -> None:
    """POST /algorithms/import must validate ownership of group and source part."""
    user_a_headers, user_b_headers = user_pair_headers

    user_a_book_id = _create_book(client, user_a_headers, "A Book")
    user_a_part_id = _create_part(client, user_a_headers, user_a_book_id)
    user_a_group_id = _create_group(client, user_a_headers, "A Group")

    user_b_book_id = _create_book(client, user_b_headers, "B Book")
    user_b_part_id = _create_part(client, user_b_headers, user_b_book_id)
    user_b_group_id = _create_group(client, user_b_headers, "B Group")

    foreign_group = client.post(
        "/api/v1/algorithms/import",
        json=_algorithm_import_payload(
            group_id=user_a_group_id,
            source_part_id=user_b_part_id,
        ),
        headers=user_b_headers,
    )
    assert foreign_group.status_code == 404
    assert foreign_group.json()["code"] == "NOT_FOUND"

    foreign_source_part = client.post(
        "/api/v1/algorithms/import",
        json=_algorithm_import_payload(
            group_id=user_b_group_id,
            source_part_id=user_a_part_id,
        ),
        headers=user_b_headers,
    )
    assert foreign_source_part.status_code == 404
    assert foreign_source_part.json()["code"] == "NOT_FOUND"


def test_algorithm_group_merge_requires_owner(
    client: TestClient,
    user_pair_headers: tuple[dict[str, str], dict[str, str]],
) -> None:
    """POST /algorithm-groups/{id}/merge must require ownership of both groups."""
    user_a_headers, user_b_headers = user_pair_headers

    source_id = _create_group(client, user_a_headers, "A Source")
    target_a_id = _create_group(client, user_a_headers, "A Target")
    target_b_id = _create_group(client, user_b_headers, "B Target")

    merge_foreign_source = client.post(
        f"/api/v1/algorithm-groups/{source_id}/merge",
        json={"target_group_id": target_b_id},
        headers=user_b_headers,
    )
    assert merge_foreign_source.status_code == 404
    assert merge_foreign_source.json()["code"] == "NOT_FOUND"

    merge_foreign_target = client.post(
        f"/api/v1/algorithm-groups/{source_id}/merge",
        json={"target_group_id": target_b_id},
        headers=user_a_headers,
    )
    assert merge_foreign_target.status_code == 404
    assert merge_foreign_target.json()["code"] == "NOT_FOUND"

    merge_owned_groups = client.post(
        f"/api/v1/algorithm-groups/{source_id}/merge",
        json={"target_group_id": target_a_id},
        headers=user_a_headers,
    )
    assert merge_owned_groups.status_code == 200


def test_export_endpoints_are_user_scoped(
    client: TestClient,
    user_pair_headers: tuple[dict[str, str], dict[str, str]],
) -> None:
    """CSV and ZIP exports must include only current user data."""
    user_a_headers, user_b_headers = user_pair_headers

    user_a_book_id = _create_book(client, user_a_headers, "A_ONLY_BOOK")
    user_a_part_id = _create_part(client, user_a_headers, user_a_book_id)
    _import_part_for_reviews(client, user_a_headers, user_a_part_id)

    user_b_book_id = _create_book(client, user_b_headers, "B_ONLY_BOOK")
    user_b_part_id = _create_part(client, user_b_headers, user_b_book_id)
    _import_part_for_reviews(client, user_b_headers, user_b_part_id)

    csv_export_a = client.get("/api/v1/export.csv", headers=user_a_headers)
    assert csv_export_a.status_code == 200
    csv_text_a = csv_export_a.content.decode("utf-8")
    assert "A_ONLY_BOOK" in csv_text_a
    assert "B_ONLY_BOOK" not in csv_text_a

    zip_export_b = client.get("/api/v1/export.zip", headers=user_b_headers)
    assert zip_export_b.status_code == 200
    with ZipFile(io.BytesIO(zip_export_b.content)) as archive:
        books_csv = archive.read("books.csv").decode("utf-8")
    rows = list(csv.DictReader(io.StringIO(books_csv)))
    titles = {row["title"] for row in rows}
    assert titles == {"B_ONLY_BOOK"}
