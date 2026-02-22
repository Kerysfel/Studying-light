"""Activity events integration tests."""

from datetime import date

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from studying_light.db.constants import (
    ACTIVITY_KIND_ALGORITHM_TRAINING_TYPING,
    ACTIVITY_KIND_READING_SESSION,
    ACTIVITY_KIND_REVIEW_ALGORITHM_THEORY,
    ACTIVITY_KIND_REVIEW_THEORY,
    ACTIVITY_SOURCE_LIVE,
    ACTIVITY_STATUS_COMPLETED,
)
from studying_light.db.models.algorithm_review_attempt import AlgorithmReviewAttempt
from studying_light.db.models.algorithm_review_item import AlgorithmReviewItem
from studying_light.db.models.review_attempt import ReviewAttempt
from studying_light.db.models.user import User
from studying_light.db.models.user_activity_event import UserActivityEvent
from studying_light.services.activity_tracker import (
    record_algorithm_training,
    record_reading_session,
    record_review_theory,
)


def _current_user(session: Session) -> User:
    return session.execute(select(User).where(User.email == "user@local")).scalar_one()


def _create_book(client: TestClient, headers: dict[str, str]) -> int:
    response = client.post(
        "/api/v1/books",
        json={"title": "Test Book"},
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()["id"]


def _create_part(
    client: TestClient,
    headers: dict[str, str],
    *,
    book_id: int,
    session_seconds: int | None = None,
    page_end: int | None = None,
) -> int:
    payload: dict = {"book_id": book_id, "label": "Part 1"}
    if session_seconds is not None:
        payload["session_seconds"] = session_seconds
    if page_end is not None:
        payload["page_end"] = page_end
    response = client.post("/api/v1/parts", json=payload, headers=headers)
    assert response.status_code == 201
    return response.json()["id"]


def _import_gpt_for_part(
    client: TestClient,
    headers: dict[str, str],
    *,
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


def _review_feedback_payload() -> dict:
    return {
        "gpt_check_result": {
            "meta": {
                "book_title": "Test Book",
                "part_index": 1,
                "part_label": "Part 1",
                "interval_days": 1,
                "review_date": date.today().isoformat(),
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
                    "short_feedback": "Good",
                    "correct_answer": "A1",
                }
            ],
        }
    }


def _algorithm_feedback_payload() -> dict:
    return {
        "gpt_check_result": {
            "meta": {
                "group_title": "Graphs",
                "algorithm_title": "BFS",
                "interval_days": 1,
                "review_date": date.today().isoformat(),
            },
            "overall": {
                "rating_1_to_5": 5,
                "key_gaps": [],
                "next_steps": [],
                "limitations": [],
            },
            "items": [
                {
                    "question": "Q1",
                    "user_answer": "A1",
                    "rating_1_to_5": 5,
                    "is_answered": True,
                    "short_feedback": "Great",
                    "correct_answer": "A1",
                    "mistakes": [],
                }
            ],
        }
    }


def _import_algorithm(
    client: TestClient,
    headers: dict[str, str],
    group_id: int,
) -> int:
    response = client.post(
        "/api/v1/algorithms/import",
        json={
            "groups": [],
            "algorithms": [
                {
                    "title": "BFS",
                    "summary": "Summary",
                    "when_to_use": "When to use",
                    "complexity": "O(1)",
                    "invariants": ["Always"],
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
        },
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()["algorithms_created"][0]["algorithm_id"]


def test_parts_create_reading_activity_event(
    client: TestClient,
    session: Session,
    auth_headers: dict[str, str],
) -> None:
    """Creating a reading part should create one reading_session activity event."""
    book_id = _create_book(client, auth_headers)
    part_id = _create_part(
        client,
        auth_headers,
        book_id=book_id,
        session_seconds=600,
        page_end=12,
    )

    user = _current_user(session)
    events = (
        session.execute(
            select(UserActivityEvent).where(
                UserActivityEvent.user_id == user.id,
                UserActivityEvent.activity_kind == ACTIVITY_KIND_READING_SESSION,
                UserActivityEvent.reading_part_id == part_id,
            )
        )
        .scalars()
        .all()
    )
    assert len(events) == 1
    event = events[0]
    assert event.book_id == book_id
    assert event.duration_sec == 600
    assert event.status == ACTIVITY_STATUS_COMPLETED
    assert event.source == ACTIVITY_SOURCE_LIVE
    assert event.meta_json is not None
    assert event.meta_json.get("page_end") == 12
    assert event.meta_json.get("pages_read") == 12


def test_reading_activity_event_is_idempotent_by_reading_part_ref(
    client: TestClient,
    session: Session,
    auth_headers: dict[str, str],
) -> None:
    """Re-recording the same reading_part_id should reuse the same event."""
    book_id = _create_book(client, auth_headers)
    part_id = _create_part(
        client,
        auth_headers,
        book_id=book_id,
        session_seconds=90,
        page_end=4,
    )
    user = _current_user(session)

    existing_event = session.execute(
        select(UserActivityEvent).where(
            UserActivityEvent.user_id == user.id,
            UserActivityEvent.activity_kind == ACTIVITY_KIND_READING_SESSION,
            UserActivityEvent.reading_part_id == part_id,
        )
    ).scalar_one()

    duplicate_result = record_reading_session(
        session,
        user_id=user.id,
        book_id=book_id,
        reading_part_id=part_id,
        ended_at=existing_event.ended_at,
        duration_sec=90,
        pages_read=4,
        page_end=4,
    )
    session.commit()

    events = (
        session.execute(
            select(UserActivityEvent).where(
                UserActivityEvent.user_id == user.id,
                UserActivityEvent.activity_kind == ACTIVITY_KIND_READING_SESSION,
                UserActivityEvent.reading_part_id == part_id,
            )
        )
        .scalars()
        .all()
    )
    assert len(events) == 1
    assert duplicate_result.id == existing_event.id


def test_algorithm_training_typing_creates_activity_event(
    client: TestClient,
    session: Session,
    auth_headers: dict[str, str],
) -> None:
    """Typing training should create one algorithm_training_typing activity event."""
    group_response = client.post(
        "/api/v1/algorithm-groups",
        json={"title": "Graphs"},
        headers=auth_headers,
    )
    assert group_response.status_code == 201
    group_id = group_response.json()["id"]
    algorithm_id = _import_algorithm(client, auth_headers, group_id)

    response = client.post(
        "/api/v1/algorithm-trainings",
        json={
            "algorithm_id": algorithm_id,
            "mode": "typing",
            "code_text": "typed code",
            "accuracy": 91.5,
            "duration_sec": 33,
        },
        headers=auth_headers,
    )
    assert response.status_code == 201
    attempt_id = response.json()["id"]

    user = _current_user(session)
    events = (
        session.execute(
            select(UserActivityEvent).where(
                UserActivityEvent.user_id == user.id,
                UserActivityEvent.activity_kind
                == ACTIVITY_KIND_ALGORITHM_TRAINING_TYPING,
                UserActivityEvent.algorithm_training_attempt_id == attempt_id,
            )
        )
        .scalars()
        .all()
    )
    assert len(events) == 1
    event = events[0]
    assert event.algorithm_id == algorithm_id
    assert event.duration_sec == 33
    assert event.accuracy == 91.5
    assert event.status == ACTIVITY_STATUS_COMPLETED
    assert event.source == ACTIVITY_SOURCE_LIVE


def test_training_activity_event_is_idempotent_by_attempt_ref(
    client: TestClient,
    session: Session,
    auth_headers: dict[str, str],
) -> None:
    """Re-recording the same training attempt should not create duplicates."""
    group_response = client.post(
        "/api/v1/algorithm-groups",
        json={"title": "Graphs"},
        headers=auth_headers,
    )
    assert group_response.status_code == 201
    group_id = group_response.json()["id"]
    algorithm_id = _import_algorithm(client, auth_headers, group_id)

    response = client.post(
        "/api/v1/algorithm-trainings",
        json={
            "algorithm_id": algorithm_id,
            "mode": "typing",
            "code_text": "typed code",
            "accuracy": 75.5,
            "duration_sec": 24,
        },
        headers=auth_headers,
    )
    assert response.status_code == 201
    attempt_id = response.json()["id"]
    user = _current_user(session)

    existing_event = session.execute(
        select(UserActivityEvent).where(
            UserActivityEvent.user_id == user.id,
            UserActivityEvent.activity_kind
            == ACTIVITY_KIND_ALGORITHM_TRAINING_TYPING,
            UserActivityEvent.algorithm_training_attempt_id == attempt_id,
        )
    ).scalar_one()

    duplicate_result = record_algorithm_training(
        session,
        user_id=user.id,
        algorithm_id=algorithm_id,
        algorithm_training_attempt_id=attempt_id,
        mode="typing",
        started_at=existing_event.started_at,
        ended_at=existing_event.ended_at,
        duration_sec=24,
        accuracy=75.5,
        rating_1_to_5=existing_event.rating_1_to_5,
    )
    session.commit()

    events = (
        session.execute(
            select(UserActivityEvent).where(
                UserActivityEvent.user_id == user.id,
                UserActivityEvent.activity_kind
                == ACTIVITY_KIND_ALGORITHM_TRAINING_TYPING,
                UserActivityEvent.algorithm_training_attempt_id == attempt_id,
            )
        )
        .scalars()
        .all()
    )
    assert len(events) == 1
    assert duplicate_result.id == existing_event.id


def test_review_theory_event_is_updated_without_duplicates(
    client: TestClient,
    session: Session,
    auth_headers: dict[str, str],
) -> None:
    """Theory review feedback should update the same activity event."""
    book_id = _create_book(client, auth_headers)
    part_id = _create_part(client, auth_headers, book_id=book_id)
    review_id = _import_gpt_for_part(client, auth_headers, part_id=part_id)

    complete_response = client.post(
        f"/api/v1/reviews/{review_id}/complete",
        json={"answers": {"Q1": "A1"}},
        headers=auth_headers,
    )
    assert complete_response.status_code == 200

    attempt = session.execute(
        select(ReviewAttempt)
        .where(ReviewAttempt.review_item_id == review_id)
        .order_by(ReviewAttempt.id.desc())
    ).scalar_one()

    user = _current_user(session)
    events_after_complete = (
        session.execute(
            select(UserActivityEvent).where(
                UserActivityEvent.user_id == user.id,
                UserActivityEvent.activity_kind == ACTIVITY_KIND_REVIEW_THEORY,
                UserActivityEvent.review_attempt_id == attempt.id,
            )
        )
        .scalars()
        .all()
    )
    assert len(events_after_complete) == 1
    assert events_after_complete[0].score_0_to_100 is None
    assert events_after_complete[0].rating_1_to_5 is None
    assert events_after_complete[0].result_label is None

    feedback_response = client.post(
        f"/api/v1/reviews/{review_id}/save_gpt_feedback",
        json=_review_feedback_payload(),
        headers=auth_headers,
    )
    assert feedback_response.status_code == 200

    events_after_feedback = (
        session.execute(
            select(UserActivityEvent).where(
                UserActivityEvent.user_id == user.id,
                UserActivityEvent.activity_kind == ACTIVITY_KIND_REVIEW_THEORY,
                UserActivityEvent.review_attempt_id == attempt.id,
            )
        )
        .scalars()
        .all()
    )
    assert len(events_after_feedback) == 1
    event = events_after_feedback[0]
    assert event.score_0_to_100 == 80
    assert event.rating_1_to_5 == 4
    assert event.result_label == "PASS"


def test_review_activity_event_is_idempotent_by_attempt_ref(
    client: TestClient,
    session: Session,
    auth_headers: dict[str, str],
) -> None:
    """Re-recording the same review attempt should reuse existing event."""
    book_id = _create_book(client, auth_headers)
    part_id = _create_part(client, auth_headers, book_id=book_id)
    review_id = _import_gpt_for_part(client, auth_headers, part_id=part_id)
    complete_response = client.post(
        f"/api/v1/reviews/{review_id}/complete",
        json={"answers": {"Q1": "A1"}},
        headers=auth_headers,
    )
    assert complete_response.status_code == 200

    attempt = session.execute(
        select(ReviewAttempt)
        .where(ReviewAttempt.review_item_id == review_id)
        .order_by(ReviewAttempt.id.desc())
    ).scalar_one()
    user = _current_user(session)

    existing_event = session.execute(
        select(UserActivityEvent).where(
            UserActivityEvent.user_id == user.id,
            UserActivityEvent.activity_kind == ACTIVITY_KIND_REVIEW_THEORY,
            UserActivityEvent.review_attempt_id == attempt.id,
        )
    ).scalar_one()

    duplicate_result = record_review_theory(
        session,
        user_id=user.id,
        review_item_id=review_id,
        reading_part_id=part_id,
        review_attempt_id=attempt.id,
        started_at=attempt.created_at,
        ended_at=existing_event.ended_at,
    )
    session.commit()

    events = (
        session.execute(
            select(UserActivityEvent).where(
                UserActivityEvent.user_id == user.id,
                UserActivityEvent.activity_kind == ACTIVITY_KIND_REVIEW_THEORY,
                UserActivityEvent.review_attempt_id == attempt.id,
            )
        )
        .scalars()
        .all()
    )
    assert len(events) == 1
    assert duplicate_result.id == existing_event.id


def test_algorithm_review_event_is_updated_without_duplicates(
    client: TestClient,
    session: Session,
    auth_headers: dict[str, str],
) -> None:
    """Algorithm review feedback should update the same activity event."""
    group_response = client.post(
        "/api/v1/algorithm-groups",
        json={"title": "Graphs"},
        headers=auth_headers,
    )
    assert group_response.status_code == 201
    group_id = group_response.json()["id"]
    algorithm_id = _import_algorithm(client, auth_headers, group_id)

    review_item = session.execute(
        select(AlgorithmReviewItem)
        .where(AlgorithmReviewItem.algorithm_id == algorithm_id)
        .order_by(AlgorithmReviewItem.id)
    ).scalars().first()
    assert review_item is not None

    complete_response = client.post(
        f"/api/v1/algorithm-reviews/{review_item.id}/complete",
        json={"answers": {"Q1": "A1"}},
        headers=auth_headers,
    )
    assert complete_response.status_code == 200

    attempt = session.execute(
        select(AlgorithmReviewAttempt)
        .where(AlgorithmReviewAttempt.review_item_id == review_item.id)
        .order_by(AlgorithmReviewAttempt.id.desc())
    ).scalar_one()

    user = _current_user(session)
    events_after_complete = (
        session.execute(
            select(UserActivityEvent).where(
                UserActivityEvent.user_id == user.id,
                UserActivityEvent.activity_kind
                == ACTIVITY_KIND_REVIEW_ALGORITHM_THEORY,
                UserActivityEvent.algorithm_review_attempt_id == attempt.id,
            )
        )
        .scalars()
        .all()
    )
    assert len(events_after_complete) == 1
    assert events_after_complete[0].rating_1_to_5 is None

    feedback_response = client.post(
        f"/api/v1/algorithm-reviews/{review_item.id}/save_gpt_feedback",
        json=_algorithm_feedback_payload(),
        headers=auth_headers,
    )
    assert feedback_response.status_code == 200

    events_after_feedback = (
        session.execute(
            select(UserActivityEvent).where(
                UserActivityEvent.user_id == user.id,
                UserActivityEvent.activity_kind
                == ACTIVITY_KIND_REVIEW_ALGORITHM_THEORY,
                UserActivityEvent.algorithm_review_attempt_id == attempt.id,
            )
        )
        .scalars()
        .all()
    )
    assert len(events_after_feedback) == 1
    assert events_after_feedback[0].rating_1_to_5 == 5
