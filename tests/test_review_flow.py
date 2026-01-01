"""Review flow integration tests."""

from datetime import date, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from studying_light.db.models.reading_part import ReadingPart


def test_part_import_creates_reviews_and_today(
    client: TestClient,
    session: Session,
) -> None:
    """Ensure import creates review items and today returns due reviews."""
    book_response = client.post("/api/v1/books", json={"title": "Test Book"})
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
    part_response = client.post("/api/v1/parts", json=part_payload)
    assert part_response.status_code == 201
    part_id = part_response.json()["id"]

    base_date = date.today() - timedelta(days=1)
    part = session.get(ReadingPart, part_id)
    assert part is not None
    part.created_at = datetime.combine(base_date, datetime.min.time())
    session.commit()

    import_payload = {
        "gpt_summary": "Summary text",
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
    )
    assert import_response.status_code == 200
    review_items = import_response.json()["review_items"]
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

    today_response = client.get("/api/v1/today")
    assert today_response.status_code == 200
    today_items = today_response.json()["review_items"]
    assert len(today_items) == 1
    assert today_items[0]["interval_days"] == 1
    assert date.fromisoformat(today_items[0]["due_date"]) == date.today()
