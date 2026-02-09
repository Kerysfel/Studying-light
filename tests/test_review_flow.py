"""Review flow integration tests."""

from datetime import date, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from studying_light.db.models.reading_part import ReadingPart
from studying_light.db.models.review_schedule_item import ReviewScheduleItem


def test_part_import_creates_reviews_and_today(
    client: TestClient,
    session: Session,
    auth_headers: dict[str, str],
) -> None:
    """Ensure import creates review items and today returns due reviews."""
    book_response = client.post(
        "/api/v1/books",
        json={"title": "Test Book"},
        headers=auth_headers,
    )
    assert book_response.status_code == 201
    book_id = book_response.json()["id"]

    part_payload = {
        "book_id": book_id,
        "label": "Part 1",
        "raw_notes": {
            "keywords": ["alpha", "beta"],
            "terms": [{"term": "Term", "definition": "Definition"}],
            "sentences": ["Sentence 1"],
            "freeform": ["Note 1"],
        },
    }
    part_response = client.post(
        "/api/v1/parts",
        json=part_payload,
        headers=auth_headers,
    )
    assert part_response.status_code == 201
    part_id = part_response.json()["id"]

    base_date = date.today() - timedelta(days=1)
    part = session.get(ReadingPart, part_id)
    assert part is not None
    part.created_at = datetime.combine(base_date, datetime.min.time())
    session.commit()

    markdown_summary = (
        "## Сводка\n\n"
        "### Ключевые идеи\n"
        "- Идея 1\n"
        "- Идея 2\n\n"
        "### Термины/инварианты\n"
        "- Термин 1\n"
        "- Термин 2\n"
    )
    import_payload = {
        "gpt_summary": markdown_summary,
        "gpt_questions_by_interval": {
            "1": ["Q1"],
            "7": ["Q2"],
            "16": ["Q3"],
            "35": ["Q4"],
            "90": ["Q5"],
        },
    }
    import_response = client.post(
        f"/api/v1/parts/{part_id}/import_gpt",
        json=import_payload,
        headers=auth_headers,
    )
    assert import_response.status_code == 200
    response_payload = import_response.json()
    assert response_payload["reading_part"]["gpt_summary"] == markdown_summary
    review_items = response_payload["review_items"]
    assert len(review_items) == 5

    expected_due = {
        1: base_date + timedelta(days=1),
        7: base_date + timedelta(days=7),
        16: base_date + timedelta(days=16),
        35: base_date + timedelta(days=35),
        90: base_date + timedelta(days=90),
    }
    for item in review_items:
        interval = item["interval_days"]
        due_date = date.fromisoformat(item["due_date"])
        assert due_date == expected_due[interval]

    stored_items = (
        session.execute(
            select(ReviewScheduleItem).where(
                ReviewScheduleItem.reading_part_id == part_id
            )
        )
        .scalars()
        .all()
    )
    stored_part = session.get(ReadingPart, part_id)
    assert stored_part is not None
    assert stored_part.gpt_summary == markdown_summary
    questions_by_interval = {
        item.interval_days: item.questions for item in stored_items
    }
    assert questions_by_interval[1] == ["Q1"]
    assert questions_by_interval[7] == ["Q2"]

    overdue_item = next(
        item for item in stored_items if item.interval_days == 7
    )
    overdue_item.due_date = date.today() - timedelta(days=1)
    session.commit()

    today_response = client.get("/api/v1/today", headers=auth_headers)
    assert today_response.status_code == 200
    today_items = today_response.json()["review_items"]
    assert len(today_items) == 1
    assert today_items[0]["interval_days"] == 1
    assert date.fromisoformat(today_items[0]["due_date"]) == date.today()
    overdue_items = today_response.json()["overdue_review_items"]
    assert len(overdue_items) == 1
    assert overdue_items[0]["interval_days"] == 7
    assert date.fromisoformat(overdue_items[0]["due_date"]) < date.today()
