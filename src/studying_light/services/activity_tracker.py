"""Activity tracking service for user activity events."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
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
from studying_light.db.models.user_activity_event import UserActivityEvent

TRAINING_MODE_TO_ACTIVITY_KIND: dict[str, str] = {
    "typing": ACTIVITY_KIND_ALGORITHM_TRAINING_TYPING,
    "memory": ACTIVITY_KIND_ALGORITHM_TRAINING_MEMORY,
}


def _merge_meta_json(
    current: dict | None,
    updates: dict | None,
) -> dict | None:
    if updates is None:
        return current
    if current is None:
        return updates
    merged = dict(current)
    merged.update(updates)
    return merged


def _find_existing_event_by_natural_ref(
    session: Session,
    *,
    activity_kind: str,
    reading_part_id: int | None = None,
    review_attempt_id: int | None = None,
    algorithm_review_attempt_id: int | None = None,
    algorithm_training_attempt_id: int | None = None,
) -> UserActivityEvent | None:
    ref_filter = None
    if reading_part_id is not None:
        ref_filter = UserActivityEvent.reading_part_id == reading_part_id
    elif review_attempt_id is not None:
        ref_filter = UserActivityEvent.review_attempt_id == review_attempt_id
    elif algorithm_review_attempt_id is not None:
        ref_filter = (
            UserActivityEvent.algorithm_review_attempt_id
            == algorithm_review_attempt_id
        )
    elif algorithm_training_attempt_id is not None:
        ref_filter = (
            UserActivityEvent.algorithm_training_attempt_id
            == algorithm_training_attempt_id
        )
    if ref_filter is None:
        return None

    return session.execute(
        select(UserActivityEvent)
        .where(
            UserActivityEvent.activity_kind == activity_kind,
            ref_filter,
        )
        .order_by(UserActivityEvent.id.desc())
        .limit(1)
    ).scalar_one_or_none()


def record_event(
    session: Session,
    *,
    user_id: UUID,
    activity_kind: str,
    status: str = ACTIVITY_STATUS_COMPLETED,
    source: str = ACTIVITY_SOURCE_LIVE,
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
    algorithm_review_item_id: int | None = None,
    algorithm_training_attempt_id: int | None = None,
    review_attempt_id: int | None = None,
    algorithm_review_attempt_id: int | None = None,
    meta_json: dict | None = None,
) -> UserActivityEvent:
    """Create and add a user activity event to the current DB transaction."""
    if duration_sec is not None and duration_sec < 0:
        raise ValueError("duration_sec must be non-negative")

    event = UserActivityEvent(
        user_id=user_id,
        activity_kind=activity_kind,
        status=status,
        source=source,
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
        algorithm_review_item_id=algorithm_review_item_id,
        algorithm_training_attempt_id=algorithm_training_attempt_id,
        review_attempt_id=review_attempt_id,
        algorithm_review_attempt_id=algorithm_review_attempt_id,
        meta_json=meta_json,
    )
    try:
        with session.begin_nested():
            session.add(event)
            session.flush()
    except IntegrityError as exc:
        existing_event = _find_existing_event_by_natural_ref(
            session,
            activity_kind=activity_kind,
            reading_part_id=reading_part_id,
            review_attempt_id=review_attempt_id,
            algorithm_review_attempt_id=algorithm_review_attempt_id,
            algorithm_training_attempt_id=algorithm_training_attempt_id,
        )
        if existing_event is None:
            raise exc
        return existing_event

    return event


def record_reading_session(
    session: Session,
    *,
    user_id: UUID,
    book_id: int,
    reading_part_id: int,
    ended_at: datetime | None,
    duration_sec: int | None,
    pages_read: int | None = None,
    page_end: int | None = None,
) -> UserActivityEvent:
    """Record a completed reading session event."""
    return record_event(
        session,
        user_id=user_id,
        activity_kind=ACTIVITY_KIND_READING_SESSION,
        ended_at=ended_at,
        duration_sec=duration_sec,
        book_id=book_id,
        reading_part_id=reading_part_id,
        meta_json={
            "pages_read": pages_read,
            "page_end": page_end,
        },
    )


def record_review_theory(
    session: Session,
    *,
    user_id: UUID,
    review_item_id: int,
    reading_part_id: int | None,
    review_attempt_id: int,
    started_at: datetime | None,
    ended_at: datetime | None,
) -> UserActivityEvent:
    """Record a completed theory review event."""
    return record_event(
        session,
        user_id=user_id,
        activity_kind=ACTIVITY_KIND_REVIEW_THEORY,
        review_item_id=review_item_id,
        reading_part_id=reading_part_id,
        review_attempt_id=review_attempt_id,
        started_at=started_at,
        ended_at=ended_at,
    )


def upsert_review_theory_feedback(
    session: Session,
    *,
    user_id: UUID,
    review_item_id: int,
    reading_part_id: int | None,
    review_attempt_id: int,
    started_at: datetime | None,
    ended_at: datetime | None,
    score_0_to_100: int | None,
    rating_1_to_5: int | None,
    result_label: str | None,
    meta_json: dict | None = None,
) -> UserActivityEvent:
    """Update existing theory review event result or create one if absent."""
    event = session.execute(
        select(UserActivityEvent)
        .where(
            UserActivityEvent.user_id == user_id,
            UserActivityEvent.activity_kind == ACTIVITY_KIND_REVIEW_THEORY,
            UserActivityEvent.review_attempt_id == review_attempt_id,
        )
        .order_by(UserActivityEvent.id.desc())
        .limit(1)
    ).scalar_one_or_none()

    if event is None:
        event = record_event(
            session,
            user_id=user_id,
            activity_kind=ACTIVITY_KIND_REVIEW_THEORY,
            review_item_id=review_item_id,
            reading_part_id=reading_part_id,
            review_attempt_id=review_attempt_id,
            started_at=started_at,
            ended_at=ended_at,
            score_0_to_100=score_0_to_100,
            rating_1_to_5=rating_1_to_5,
            result_label=result_label,
            meta_json=meta_json,
        )

    event.score_0_to_100 = score_0_to_100
    event.rating_1_to_5 = rating_1_to_5
    event.result_label = result_label
    event.meta_json = _merge_meta_json(event.meta_json, meta_json)
    if reading_part_id is not None:
        event.reading_part_id = reading_part_id
    event.review_item_id = review_item_id
    event.review_attempt_id = review_attempt_id
    event.started_at = event.started_at or started_at
    event.ended_at = ended_at or event.ended_at
    return event


def record_algorithm_review_theory(
    session: Session,
    *,
    user_id: UUID,
    algorithm_id: int,
    algorithm_review_item_id: int,
    algorithm_review_attempt_id: int,
    started_at: datetime | None,
    ended_at: datetime | None,
) -> UserActivityEvent:
    """Record a completed algorithm theory review event."""
    return record_event(
        session,
        user_id=user_id,
        activity_kind=ACTIVITY_KIND_REVIEW_ALGORITHM_THEORY,
        algorithm_id=algorithm_id,
        algorithm_review_item_id=algorithm_review_item_id,
        algorithm_review_attempt_id=algorithm_review_attempt_id,
        started_at=started_at,
        ended_at=ended_at,
    )


def upsert_algorithm_review_theory_feedback(
    session: Session,
    *,
    user_id: UUID,
    algorithm_id: int,
    algorithm_review_item_id: int,
    algorithm_review_attempt_id: int,
    started_at: datetime | None,
    ended_at: datetime | None,
    score_0_to_100: int | None,
    rating_1_to_5: int | None,
    result_label: str | None,
    meta_json: dict | None = None,
) -> UserActivityEvent:
    """Update existing algorithm theory review event result or create one."""
    event = session.execute(
        select(UserActivityEvent)
        .where(
            UserActivityEvent.user_id == user_id,
            UserActivityEvent.activity_kind == ACTIVITY_KIND_REVIEW_ALGORITHM_THEORY,
            UserActivityEvent.algorithm_review_attempt_id
            == algorithm_review_attempt_id,
        )
        .order_by(UserActivityEvent.id.desc())
        .limit(1)
    ).scalar_one_or_none()

    if event is None:
        event = record_event(
            session,
            user_id=user_id,
            activity_kind=ACTIVITY_KIND_REVIEW_ALGORITHM_THEORY,
            algorithm_id=algorithm_id,
            algorithm_review_item_id=algorithm_review_item_id,
            algorithm_review_attempt_id=algorithm_review_attempt_id,
            started_at=started_at,
            ended_at=ended_at,
            score_0_to_100=score_0_to_100,
            rating_1_to_5=rating_1_to_5,
            result_label=result_label,
            meta_json=meta_json,
        )

    event.score_0_to_100 = score_0_to_100
    event.rating_1_to_5 = rating_1_to_5
    event.result_label = result_label
    event.meta_json = _merge_meta_json(event.meta_json, meta_json)
    event.algorithm_id = algorithm_id
    event.algorithm_review_item_id = algorithm_review_item_id
    event.algorithm_review_attempt_id = algorithm_review_attempt_id
    event.started_at = event.started_at or started_at
    event.ended_at = ended_at or event.ended_at
    return event


def record_algorithm_training(
    session: Session,
    *,
    user_id: UUID,
    algorithm_id: int,
    algorithm_training_attempt_id: int,
    mode: str,
    started_at: datetime | None,
    ended_at: datetime | None,
    duration_sec: int | None,
    accuracy: float | None,
    rating_1_to_5: int | None,
    score_0_to_100: int | None = None,
    result_label: str | None = None,
    meta_json: dict | None = None,
) -> UserActivityEvent:
    """Record a completed algorithm training event."""
    activity_kind = TRAINING_MODE_TO_ACTIVITY_KIND.get(mode)
    if activity_kind is None:
        raise ValueError(f"Unsupported training mode: {mode}")

    training_meta = _merge_meta_json({"mode": mode}, meta_json)
    return record_event(
        session,
        user_id=user_id,
        activity_kind=activity_kind,
        algorithm_id=algorithm_id,
        algorithm_training_attempt_id=algorithm_training_attempt_id,
        started_at=started_at,
        ended_at=ended_at,
        duration_sec=duration_sec,
        accuracy=accuracy,
        rating_1_to_5=rating_1_to_5,
        score_0_to_100=score_0_to_100,
        result_label=result_label,
        meta_json=training_meta,
    )
