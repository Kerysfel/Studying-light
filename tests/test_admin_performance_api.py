"""Admin performance API tests."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from studying_light.db.constants import (
    ACTIVITY_KIND_ALGORITHM_TRAINING_MEMORY,
    ACTIVITY_KIND_ALGORITHM_TRAINING_TYPING,
    ACTIVITY_KIND_READING_SESSION,
    ACTIVITY_KIND_REVIEW_ALGORITHM_THEORY,
    ACTIVITY_KIND_REVIEW_THEORY,
    ACTIVITY_SOURCE_LIVE,
    ACTIVITY_STATUS_COMPLETED,
)
from studying_light.db.models.algorithm import Algorithm
from studying_light.db.models.algorithm_group import AlgorithmGroup
from studying_light.db.models.book import Book
from studying_light.db.models.reading_part import ReadingPart
from studying_light.db.models.user import User
from studying_light.db.models.user_activity_event import UserActivityEvent


def _register(client, email: str, password: str = "strongpass123") -> None:
    response = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password},
    )
    assert response.status_code == 201


def _activate_user(
    session: Session,
    *,
    email: str,
    is_admin: bool = False,
) -> User:
    user = session.execute(select(User).where(User.email == email)).scalar_one()
    user.is_active = True
    user.is_admin = is_admin
    session.commit()
    session.refresh(user)
    return user


def _login(client, email: str, password: str = "strongpass123") -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _admin_headers(client, session: Session) -> dict[str, str]:
    _register(client, "perf-admin@example.com")
    _activate_user(session, email="perf-admin@example.com", is_admin=True)
    return _login(client, "perf-admin@example.com")


def _user_headers(client, session: Session, email: str) -> dict[str, str]:
    _register(client, email)
    _activate_user(session, email=email, is_admin=False)
    return _login(client, email)


def _event(
    *,
    user_id,
    activity_kind: str,
    created_at: datetime,
    started_at: datetime | None = None,
    ended_at: datetime | None = None,
    duration_sec: int | None = None,
    score_0_to_100: int | None = None,
    rating_1_to_5: int | None = None,
    result_label: str | None = None,
    accuracy: float | None = None,
    book_id: int | None = None,
    reading_part_id: int | None = None,
    review_item_id: int | None = None,
    algorithm_id: int | None = None,
) -> UserActivityEvent:
    return UserActivityEvent(
        user_id=user_id,
        activity_kind=activity_kind,
        status=ACTIVITY_STATUS_COMPLETED,
        source=ACTIVITY_SOURCE_LIVE,
        created_at=created_at,
        started_at=started_at,
        ended_at=ended_at,
        duration_sec=duration_sec,
        score_0_to_100=score_0_to_100,
        rating_1_to_5=rating_1_to_5,
        result_label=result_label,
        accuracy=accuracy,
        book_id=book_id,
        reading_part_id=reading_part_id,
        review_item_id=review_item_id,
        algorithm_id=algorithm_id,
    )


def test_admin_users_performance_list_returns_aggregates(
    client,
    session: Session,
) -> None:
    """Admin list endpoint should return grouped performance metrics."""
    admin_headers = _admin_headers(client, session)
    _user_headers(client, session, "perf-user-a@example.com")
    _user_headers(client, session, "perf-user-b@example.com")

    user_a = session.execute(
        select(User).where(User.email == "perf-user-a@example.com")
    ).scalar_one()
    user_b = session.execute(
        select(User).where(User.email == "perf-user-b@example.com")
    ).scalar_one()

    now = datetime.now(timezone.utc)
    session.add_all(
        [
            _event(
                user_id=user_a.id,
                activity_kind=ACTIVITY_KIND_READING_SESSION,
                created_at=now - timedelta(hours=6),
                ended_at=now - timedelta(hours=6),
                duration_sec=600,
            ),
            _event(
                user_id=user_a.id,
                activity_kind=ACTIVITY_KIND_REVIEW_THEORY,
                created_at=now - timedelta(hours=5),
                ended_at=now - timedelta(hours=5),
                rating_1_to_5=4,
                score_0_to_100=80,
                result_label="PASS",
            ),
            _event(
                user_id=user_a.id,
                activity_kind=ACTIVITY_KIND_REVIEW_ALGORITHM_THEORY,
                created_at=now - timedelta(hours=4),
                ended_at=now - timedelta(hours=4),
                rating_1_to_5=5,
            ),
            _event(
                user_id=user_a.id,
                activity_kind=ACTIVITY_KIND_ALGORITHM_TRAINING_TYPING,
                created_at=now - timedelta(hours=3),
                ended_at=now - timedelta(hours=3),
                duration_sec=40,
                accuracy=92.5,
                rating_1_to_5=5,
            ),
            _event(
                user_id=user_a.id,
                activity_kind=ACTIVITY_KIND_ALGORITHM_TRAINING_MEMORY,
                created_at=now - timedelta(hours=2),
                ended_at=now - timedelta(hours=2),
                duration_sec=55,
                rating_1_to_5=4,
            ),
            _event(
                user_id=user_b.id,
                activity_kind=ACTIVITY_KIND_READING_SESSION,
                created_at=now - timedelta(hours=1),
                ended_at=now - timedelta(hours=1),
                duration_sec=120,
            ),
        ]
    )
    session.commit()

    response = client.get(
        "/api/v1/admin/users/performance",
        params={"sort_by": "total_activity_count", "sort_dir": "desc"},
        headers=admin_headers,
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 2

    first = payload["items"][0]
    assert first["email"] == "perf-user-a@example.com"
    assert first["total_activity_count"] == 5
    assert first["reading_sessions_count"] == 1
    assert first["reading_total_duration_sec"] == 600
    assert first["review_theory_count"] == 1
    assert first["review_theory_avg_rating"] == 4.0
    assert first["review_theory_avg_score"] == 80.0
    assert first["review_algorithm_theory_count"] == 1
    assert first["review_algorithm_theory_avg_rating"] == 5.0
    assert first["training_typing_count"] == 1
    assert first["training_typing_total_duration_sec"] == 40
    assert first["training_memory_count"] == 1
    assert first["training_memory_total_duration_sec"] == 55

    second = payload["items"][1]
    assert second["email"] == "perf-user-b@example.com"
    assert second["total_activity_count"] == 1
    assert second["reading_sessions_count"] == 1


def test_admin_user_performance_detail_supports_date_filter(
    client,
    session: Session,
) -> None:
    """Detail endpoint should compute summary and apply date filters."""
    admin_headers = _admin_headers(client, session)
    _user_headers(client, session, "detail-user@example.com")

    user = session.execute(
        select(User).where(User.email == "detail-user@example.com")
    ).scalar_one()

    now = datetime.now(timezone.utc)
    yesterday = now - timedelta(days=1)
    session.add_all(
        [
            _event(
                user_id=user.id,
                activity_kind=ACTIVITY_KIND_READING_SESSION,
                created_at=yesterday,
                ended_at=yesterday,
                duration_sec=500,
            ),
            _event(
                user_id=user.id,
                activity_kind=ACTIVITY_KIND_READING_SESSION,
                created_at=now - timedelta(hours=6),
                ended_at=now - timedelta(hours=6),
                duration_sec=120,
            ),
            _event(
                user_id=user.id,
                activity_kind=ACTIVITY_KIND_REVIEW_THEORY,
                created_at=now - timedelta(hours=5),
                ended_at=now - timedelta(hours=5),
                rating_1_to_5=4,
                score_0_to_100=80,
            ),
            _event(
                user_id=user.id,
                activity_kind=ACTIVITY_KIND_REVIEW_THEORY,
                created_at=now - timedelta(hours=4),
                ended_at=now - timedelta(hours=4),
                rating_1_to_5=2,
                score_0_to_100=60,
            ),
            _event(
                user_id=user.id,
                activity_kind=ACTIVITY_KIND_REVIEW_ALGORITHM_THEORY,
                created_at=now - timedelta(hours=3),
                ended_at=now - timedelta(hours=3),
                rating_1_to_5=5,
            ),
            _event(
                user_id=user.id,
                activity_kind=ACTIVITY_KIND_ALGORITHM_TRAINING_TYPING,
                created_at=now - timedelta(hours=2),
                ended_at=now - timedelta(hours=2),
                duration_sec=30,
                accuracy=90,
                rating_1_to_5=5,
            ),
            _event(
                user_id=user.id,
                activity_kind=ACTIVITY_KIND_ALGORITHM_TRAINING_MEMORY,
                created_at=now - timedelta(hours=1),
                ended_at=now - timedelta(hours=1),
                duration_sec=50,
                rating_1_to_5=4,
            ),
        ]
    )
    session.commit()

    today_iso = date.today().isoformat()
    response = client.get(
        f"/api/v1/admin/users/{user.id}/performance",
        params={"date_from": today_iso, "date_to": today_iso},
        headers=admin_headers,
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["email"] == "detail-user@example.com"
    assert payload["total_activity_count"] == 6

    reading = payload["reading"]
    assert reading["sessions_count"] == 1
    assert reading["total_duration_sec"] == 120
    assert reading["avg_duration_sec"] == 120.0

    review_theory = payload["review_theory"]
    assert review_theory["attempts_count"] == 2
    assert review_theory["avg_rating"] == 3.0
    assert review_theory["avg_score"] == 70.0
    assert review_theory["last_rating"] == 2.0
    assert review_theory["last_score"] == 60.0

    review_algorithm = payload["review_algorithm_theory"]
    assert review_algorithm["attempts_count"] == 1
    assert review_algorithm["avg_rating"] == 5.0
    assert review_algorithm["last_rating"] == 5.0

    typing = payload["training_typing"]
    assert typing["attempts_count"] == 1
    assert typing["total_duration_sec"] == 30
    assert typing["avg_duration_sec"] == 30.0
    assert typing["avg_accuracy"] == 90.0
    assert typing["avg_rating"] == 5.0

    memory = payload["training_memory"]
    assert memory["attempts_count"] == 1
    assert memory["total_duration_sec"] == 50
    assert memory["avg_duration_sec"] == 50.0
    assert memory["avg_rating"] == 4.0


def test_admin_user_activities_order_and_kind_filter(
    client,
    session: Session,
) -> None:
    """Activities endpoint should return deterministic order and kind filter."""
    admin_headers = _admin_headers(client, session)
    _user_headers(client, session, "activities-user@example.com")

    user = session.execute(
        select(User).where(User.email == "activities-user@example.com")
    ).scalar_one()

    book = Book(user_id=user.id, title="Distributed Systems", status="active")
    session.add(book)
    session.flush()
    part = ReadingPart(
        user_id=user.id,
        book_id=book.id,
        part_index=2,
        label="Chapter 2",
    )
    session.add(part)
    session.flush()

    group = AlgorithmGroup(user_id=user.id, title="Graphs")
    session.add(group)
    session.flush()
    algorithm = Algorithm(
        user_id=user.id,
        group_id=group.id,
        title="Dijkstra",
        summary="Summary",
        when_to_use="When",
        complexity="O(E log V)",
        invariants=["Invariant"],
        steps=["Step"],
        corner_cases=["Case"],
    )
    session.add(algorithm)
    session.flush()

    base = datetime.now(timezone.utc) - timedelta(days=1)
    event_reading = _event(
        user_id=user.id,
        activity_kind=ACTIVITY_KIND_READING_SESSION,
        created_at=base + timedelta(hours=1),
        ended_at=None,
        duration_sec=100,
        book_id=book.id,
        reading_part_id=part.id,
    )
    event_review = _event(
        user_id=user.id,
        activity_kind=ACTIVITY_KIND_REVIEW_THEORY,
        created_at=base + timedelta(hours=2),
        started_at=base + timedelta(hours=2),
        ended_at=base + timedelta(hours=3),
        score_0_to_100=77,
        rating_1_to_5=4,
        reading_part_id=part.id,
    )
    event_training = _event(
        user_id=user.id,
        activity_kind=ACTIVITY_KIND_ALGORITHM_TRAINING_TYPING,
        created_at=base + timedelta(hours=4),
        started_at=base + timedelta(hours=2),
        ended_at=base + timedelta(hours=2, minutes=30),
        duration_sec=33,
        accuracy=88,
        rating_1_to_5=4,
        algorithm_id=algorithm.id,
    )
    session.add_all([event_reading, event_review, event_training])
    session.commit()

    response = client.get(
        f"/api/v1/admin/users/{user.id}/activities",
        headers=admin_headers,
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 3

    ids = [item["id"] for item in payload["items"]]
    assert ids == [event_review.id, event_training.id, event_reading.id]
    assert payload["items"][0]["book_title"] == "Distributed Systems"
    assert payload["items"][0]["reading_part_label"] == "Chapter 2"
    assert payload["items"][1]["algorithm_title"] == "Dijkstra"
    assert payload["items"][2]["book_title"] == "Distributed Systems"

    filtered = client.get(
        f"/api/v1/admin/users/{user.id}/activities",
        params={"activity_kind": ACTIVITY_KIND_REVIEW_THEORY},
        headers=admin_headers,
    )
    assert filtered.status_code == 200
    filtered_payload = filtered.json()
    assert filtered_payload["total"] == 1
    assert len(filtered_payload["items"]) == 1
    assert filtered_payload["items"][0]["activity_kind"] == ACTIVITY_KIND_REVIEW_THEORY


def test_non_admin_forbidden_for_performance_routes(
    client,
    session: Session,
) -> None:
    """Non-admin users should not access admin performance endpoints."""
    user_headers = _user_headers(client, session, "regular-performance@example.com")

    response = client.get(
        "/api/v1/admin/users/performance",
        headers=user_headers,
    )
    assert response.status_code == 403
    assert response.json()["code"] == "FORBIDDEN"
