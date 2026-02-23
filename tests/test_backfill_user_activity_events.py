"""Backfill tests for user_activity_events."""

from __future__ import annotations

from datetime import date, datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from studying_light.db.constants import (
    ACTIVITY_KIND_ALGORITHM_TRAINING_MEMORY,
    ACTIVITY_KIND_ALGORITHM_TRAINING_TYPING,
    ACTIVITY_KIND_READING_SESSION,
    ACTIVITY_KIND_REVIEW_ALGORITHM_THEORY,
    ACTIVITY_KIND_REVIEW_THEORY,
    ACTIVITY_SOURCE_BACKFILL,
    ACTIVITY_STATUS_COMPLETED,
)
from studying_light.db.models.algorithm import Algorithm
from studying_light.db.models.algorithm_group import AlgorithmGroup
from studying_light.db.models.algorithm_review_attempt import AlgorithmReviewAttempt
from studying_light.db.models.algorithm_review_item import AlgorithmReviewItem
from studying_light.db.models.algorithm_training_attempt import AlgorithmTrainingAttempt
from studying_light.db.models.book import Book
from studying_light.db.models.reading_part import ReadingPart
from studying_light.db.models.review_attempt import ReviewAttempt
from studying_light.db.models.review_schedule_item import ReviewScheduleItem
from studying_light.db.models.user import User
from studying_light.db.models.user_activity_event import UserActivityEvent
from studying_light.services.backfill_user_activity_events import (
    GROUP_READING,
    GROUP_REVIEW_ALGORITHM,
    GROUP_REVIEW_THEORY,
    GROUP_TRAINING,
    backfill_user_activity_events,
)


def _make_user(session: Session, email: str) -> User:
    user = User(email=email, password_hash="hash")
    session.add(user)
    session.flush()
    return user


def test_backfill_user_activity_events_transfers_historical_data(
    session: Session,
) -> None:
    """Backfill should map historical rows into normalized activity events."""
    user = _make_user(session, "backfill-user@example.com")

    book = Book(user_id=user.id, title="Book", status="active")
    session.add(book)
    session.flush()

    part_good = ReadingPart(
        user_id=user.id,
        book_id=book.id,
        part_index=1,
        label="Part 1",
        created_at=datetime(2025, 1, 10, 10, 0, tzinfo=timezone.utc),
        session_seconds=600,
        pages_read=10,
        page_end=10,
    )
    part_bad_duration = ReadingPart(
        user_id=user.id,
        book_id=book.id,
        part_index=2,
        label="Part 2",
        created_at=datetime(2025, 1, 10, 12, 0, tzinfo=timezone.utc),
        session_seconds=-30,
        pages_read=4,
        page_end=14,
    )
    session.add_all([part_good, part_bad_duration])
    session.flush()

    review_item = ReviewScheduleItem(
        user_id=user.id,
        reading_part_id=part_good.id,
        interval_days=1,
        due_date=date(2025, 1, 11),
        status="done",
        completed_at=datetime(2025, 1, 11, 9, 0, tzinfo=timezone.utc),
        questions=["Q1"],
    )
    session.add(review_item)
    session.flush()

    review_attempt = ReviewAttempt(
        user_id=user.id,
        review_item_id=review_item.id,
        answers={"Q1": "A1"},
        created_at=datetime(2025, 1, 11, 8, 50, tzinfo=timezone.utc),
        gpt_rating_1_to_5=4,
        gpt_score_0_to_100=82,
        gpt_verdict="PASS",
    )
    session.add(review_attempt)

    group = AlgorithmGroup(user_id=user.id, title="Graphs")
    session.add(group)
    session.flush()

    algorithm = Algorithm(
        user_id=user.id,
        group_id=group.id,
        title="BFS",
        summary="Summary",
        when_to_use="When",
        complexity="O(V+E)",
        invariants=["Inv"],
        steps=["Step"],
        corner_cases=["Case"],
    )
    session.add(algorithm)
    session.flush()

    algorithm_review_item = AlgorithmReviewItem(
        user_id=user.id,
        algorithm_id=algorithm.id,
        interval_days=1,
        due_date=date(2025, 1, 12),
        status="done",
        completed_at=datetime(2025, 1, 12, 9, 0, tzinfo=timezone.utc),
        questions=["Q"],
    )
    session.add(algorithm_review_item)
    session.flush()

    algorithm_review_attempt = AlgorithmReviewAttempt(
        user_id=user.id,
        review_item_id=algorithm_review_item.id,
        answers={"Q": "A"},
        rating_1_to_5=5,
        created_at=datetime(2025, 1, 12, 8, 55, tzinfo=timezone.utc),
    )
    session.add(algorithm_review_attempt)

    training_typing = AlgorithmTrainingAttempt(
        user_id=user.id,
        algorithm_id=algorithm.id,
        mode="typing",
        code_text="print('typing')",
        duration_sec=45,
        accuracy=91.5,
        rating_1_to_5=5,
        created_at=datetime(2025, 1, 13, 8, 0, tzinfo=timezone.utc),
    )
    training_memory = AlgorithmTrainingAttempt(
        user_id=user.id,
        algorithm_id=algorithm.id,
        mode="memory",
        code_text="print('memory')",
        duration_sec=90,
        rating_1_to_5=4,
        created_at=datetime(2025, 1, 13, 9, 0, tzinfo=timezone.utc),
    )
    session.add_all([training_typing, training_memory])
    session.commit()

    report = backfill_user_activity_events(session, dry_run=False, batch_size=2)

    assert report.groups[GROUP_READING].created == 2
    assert report.groups[GROUP_READING].skipped_invalid == 1
    assert report.groups[GROUP_REVIEW_THEORY].created == 1
    assert report.groups[GROUP_REVIEW_ALGORITHM].created == 1
    assert report.groups[GROUP_TRAINING].created == 2

    events = session.execute(select(UserActivityEvent)).scalars().all()
    assert len(events) == 6
    assert all(event.source == ACTIVITY_SOURCE_BACKFILL for event in events)
    assert all(event.status == ACTIVITY_STATUS_COMPLETED for event in events)

    reading_events = {
        event.reading_part_id: event
        for event in events
        if event.activity_kind == ACTIVITY_KIND_READING_SESSION
    }
    assert set(reading_events.keys()) == {part_good.id, part_bad_duration.id}
    assert reading_events[part_good.id].duration_sec == 600
    assert reading_events[part_good.id].started_at is not None
    assert reading_events[part_bad_duration.id].duration_sec is None
    assert reading_events[part_bad_duration.id].started_at is None

    theory_event = session.execute(
        select(UserActivityEvent).where(
            UserActivityEvent.activity_kind == ACTIVITY_KIND_REVIEW_THEORY,
            UserActivityEvent.review_attempt_id == review_attempt.id,
        )
    ).scalar_one()
    assert theory_event.review_item_id == review_item.id
    assert theory_event.reading_part_id == part_good.id
    assert theory_event.rating_1_to_5 == 4
    assert theory_event.score_0_to_100 == 82
    assert theory_event.result_label == "PASS"

    algorithm_theory_event = session.execute(
        select(UserActivityEvent).where(
            UserActivityEvent.activity_kind == ACTIVITY_KIND_REVIEW_ALGORITHM_THEORY,
            UserActivityEvent.algorithm_review_attempt_id
            == algorithm_review_attempt.id,
        )
    ).scalar_one()
    assert algorithm_theory_event.algorithm_id == algorithm.id
    assert algorithm_theory_event.rating_1_to_5 == 5

    typing_event = session.execute(
        select(UserActivityEvent).where(
            UserActivityEvent.algorithm_training_attempt_id == training_typing.id,
            UserActivityEvent.activity_kind == ACTIVITY_KIND_ALGORITHM_TRAINING_TYPING,
        )
    ).scalar_one()
    assert typing_event.duration_sec == 45
    assert typing_event.accuracy == 91.5

    memory_event = session.execute(
        select(UserActivityEvent).where(
            UserActivityEvent.algorithm_training_attempt_id == training_memory.id,
            UserActivityEvent.activity_kind == ACTIVITY_KIND_ALGORITHM_TRAINING_MEMORY,
        )
    ).scalar_one()
    assert memory_event.duration_sec == 90

    second_run = backfill_user_activity_events(session, dry_run=False, batch_size=2)
    assert second_run.total.created == 0
    assert second_run.groups[GROUP_READING].skipped_duplicates == 2
    assert second_run.groups[GROUP_REVIEW_THEORY].skipped_duplicates == 1
    assert second_run.groups[GROUP_REVIEW_ALGORITHM].skipped_duplicates == 1
    assert second_run.groups[GROUP_TRAINING].skipped_duplicates == 2

    total_after_second = session.execute(select(UserActivityEvent)).scalars().all()
    assert len(total_after_second) == 6


def test_backfill_dry_run_does_not_write_events(session: Session) -> None:
    """Dry-run should report inserts but keep user_activity_events unchanged."""
    user = _make_user(session, "dry-run@example.com")
    book = Book(user_id=user.id, title="Dry", status="active")
    session.add(book)
    session.flush()

    part = ReadingPart(
        user_id=user.id,
        book_id=book.id,
        part_index=1,
        created_at=datetime(2025, 1, 20, 10, 0, tzinfo=timezone.utc),
        session_seconds=120,
    )
    session.add(part)
    session.commit()

    report = backfill_user_activity_events(session, dry_run=True, batch_size=10)
    assert report.groups[GROUP_READING].created == 1

    events = session.execute(select(UserActivityEvent)).scalars().all()
    assert events == []
