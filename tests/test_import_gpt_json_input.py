"""Tests for robust GPT JSON import parsing and error classification."""

from __future__ import annotations

import json

from fastapi.testclient import TestClient


def _create_part(client: TestClient, auth_headers: dict[str, str]) -> int:
    book_response = client.post(
        "/api/v1/books",
        json={"title": "GPT Import Book"},
        headers=auth_headers,
    )
    assert book_response.status_code == 201
    book_id = book_response.json()["id"]

    part_response = client.post(
        "/api/v1/parts",
        json={"book_id": book_id, "label": "Part"},
        headers=auth_headers,
    )
    assert part_response.status_code == 201
    return part_response.json()["id"]


def _base_import_payload() -> dict[str, object]:
    return {
        "gpt_summary": "## Summary\n\n### Ключевые идеи\n- One",
        "gpt_questions_by_interval": {
            "1": ["Q1"],
            "7": ["Q2"],
            "16": ["Q3"],
            "35": ["Q4"],
            "90": ["Q5"],
        },
    }


def test_import_gpt_accepts_raw_stringified_json(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    """Endpoint should accept raw string body containing a JSON object."""
    part_id = _create_part(client, auth_headers)
    raw_payload = json.dumps(_base_import_payload(), ensure_ascii=False)

    response = client.post(
        f"/api/v1/parts/{part_id}/import_gpt",
        json=raw_payload,
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert len(response.json()["review_items"]) == 5


def test_import_gpt_accepts_json_code_fence(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    """Endpoint should parse GPT output wrapped in ```json fences."""
    part_id = _create_part(client, auth_headers)
    fenced_payload = (
        "```json\n"
        f"{json.dumps(_base_import_payload(), ensure_ascii=False, indent=2)}\n"
        "```"
    )

    response = client.post(
        f"/api/v1/parts/{part_id}/import_gpt",
        json=fenced_payload,
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert len(response.json()["review_items"]) == 5


def test_import_gpt_accepts_typographic_quotes(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    """Endpoint should normalize smart quotes before JSON parsing."""
    part_id = _create_part(client, auth_headers)
    smart_quote_payload = (
        "“gpt_summary”: “## Summary\\n\\n### Ключевые идеи\\n- One”,"
        " “gpt_questions_by_interval”: {“1”: [“Q1”], “7”: [“Q2”],"
        " “16”: [“Q3”], “35”: [“Q4”], “90”: [“Q5”]}"
    )
    smart_quote_payload = f"{{{smart_quote_payload}}}"

    response = client.post(
        f"/api/v1/parts/{part_id}/import_gpt",
        json=smart_quote_payload,
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert len(response.json()["review_items"]) == 5


def test_import_gpt_accepts_text_around_json(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    """Endpoint should extract JSON object from surrounding plain text."""
    part_id = _create_part(client, auth_headers)
    wrapped_payload = (
        "Вот результат:\n"
        f"{json.dumps(_base_import_payload(), ensure_ascii=False)}\n"
        "Готово."
    )

    response = client.post(
        f"/api/v1/parts/{part_id}/import_gpt",
        json=wrapped_payload,
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert len(response.json()["review_items"]) == 5


def test_import_gpt_returns_invalid_json_syntax_for_bad_payload(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    """Syntax errors should return INVALID_JSON_SYNTAX."""
    part_id = _create_part(client, auth_headers)
    bad_payload = "```json\n{\"gpt_summary\":\"x\",}\n```"

    response = client.post(
        f"/api/v1/parts/{part_id}/import_gpt",
        json=bad_payload,
        headers=auth_headers,
    )

    assert response.status_code == 422
    body = response.json()
    assert body["code"] == "INVALID_JSON_SYNTAX"


def test_import_gpt_returns_invalid_json_schema_for_missing_required_field(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    """Schema errors should return INVALID_JSON_SCHEMA."""
    part_id = _create_part(client, auth_headers)
    schema_invalid_payload = json.dumps(
        {
            "gpt_questions_by_interval": {
                "1": ["Q1"],
                "7": ["Q2"],
                "16": ["Q3"],
                "35": ["Q4"],
                "90": ["Q5"],
            }
        },
        ensure_ascii=False,
    )

    response = client.post(
        f"/api/v1/parts/{part_id}/import_gpt",
        json=schema_invalid_payload,
        headers=auth_headers,
    )

    assert response.status_code == 422
    body = response.json()
    assert body["code"] == "INVALID_JSON_SCHEMA"
