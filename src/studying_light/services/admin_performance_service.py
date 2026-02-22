"""Admin read-side service for user performance analytics."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from studying_light.db.constants import (
    ACTIVITY_KIND_ALGORITHM_TRAINING_MEMORY,
    ACTIVITY_KIND_ALGORITHM_TRAINING_TYPING,
    ACTIVITY_KIND_READING_SESSION,
    ACTIVITY_KIND_REVIEW_ALGORITHM_THEORY,
    ACTIVITY_KIND_REVIEW_THEORY,
    USER_ACTIVITY_KINDS,
)
from studying_light.db.models.algorithm import Algorithm
from studying_light.db.models.book import Book
from studying_light.db.models.reading_part import ReadingPart
from studying_light.db.models.user import User
from studying_light.db.models.user_activity_event import UserActivityEvent

USER_PERFORMANCE_SORT_FIELDS: tuple[str, ...] = (
    "last_activity_at",
    "reading_sessions",
    "total_activity_count",
)
USER_PERFORMANCE_SORT_DIRECTIONS: tuple[str, ...] = ("asc", "desc")


def _event_time_expr():
    return func.coalesce(UserActivityEvent.ended_at, UserActivityEvent.created_at)


def _to_datetime_bounds(
    *,
    date_from: date | None,
    date_to: date | None,
) -> tuple[datetime | None, datetime | None]:
    if date_from is not None and date_to is not None and date_from > date_to:
        raise ValueError("date_from must be less than or equal to date_to")

    start = (
        datetime.combine(date_from, time.min, tzinfo=timezone.utc)
        if date_from is not None
        else None
    )
    end_exclusive = (
        datetime.combine(date_to + timedelta(days=1), time.min, tzinfo=timezone.utc)
        if date_to is not None
        else None
    )
    return start, end_exclusive


def _build_event_filters(
    *,
    user_id: UUID | None = None,
    activity_kind: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
) -> list:
    event_time = _event_time_expr()
    start, end_exclusive = _to_datetime_bounds(date_from=date_from, date_to=date_to)

    filters: list = []
    if user_id is not None:
        filters.append(UserActivityEvent.user_id == user_id)
    if activity_kind is not None:
        filters.append(UserActivityEvent.activity_kind == activity_kind)
    if start is not None:
        filters.append(event_time >= start)
    if end_exclusive is not None:
        filters.append(event_time < end_exclusive)
    return filters


def _avg_for_kind(kind: str, column) -> Any:
    return func.avg(
        case(
            (UserActivityEvent.activity_kind == kind, column),
            else_=None,
        )
    )


def _count_for_kind(kind: str) -> Any:
    return func.coalesce(
        func.sum(
            case(
                (UserActivityEvent.activity_kind == kind, 1),
                else_=0,
            )
        ),
        0,
    )


def _duration_sum_for_kind(kind: str) -> Any:
    return func.coalesce(
        func.sum(
            case(
                (
                    UserActivityEvent.activity_kind == kind,
                    func.coalesce(UserActivityEvent.duration_sec, 0),
                ),
                else_=0,
            )
        ),
        0,
    )


def _to_int(value: Any) -> int:
    if value is None:
        return 0
    return int(value)


def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    return round(float(value), 2)


def _last_value_subquery(
    *,
    user_id: UUID,
    activity_kind: str,
    value_column,
    date_from: date | None,
    date_to: date | None,
):
    event_time = _event_time_expr()
    filters = _build_event_filters(
        user_id=user_id,
        activity_kind=activity_kind,
        date_from=date_from,
        date_to=date_to,
    )
    filters.append(value_column.is_not(None))
    return (
        select(value_column)
        .where(*filters)
        .order_by(event_time.desc(), UserActivityEvent.id.desc())
        .limit(1)
        .scalar_subquery()
    )


def get_user_identity(
    session: Session,
    *,
    user_id: UUID,
) -> dict[str, Any] | None:
    """Return basic user identity for admin screens."""
    row = session.execute(
        select(User.id, User.email).where(User.id == user_id)
    ).one_or_none()
    if row is None:
        return None
    return {
        "user_id": row.id,
        "email": row.email,
        "name": None,
    }


def list_users_performance(
    session: Session,
    *,
    search: str | None,
    date_from: date | None,
    date_to: date | None,
    limit: int,
    offset: int,
    sort_by: str,
    sort_dir: str,
) -> tuple[list[dict[str, Any]], int]:
    """List users with aggregated performance metrics."""
    normalized_sort_by = sort_by.strip().lower()
    if normalized_sort_by not in USER_PERFORMANCE_SORT_FIELDS:
        allowed = ", ".join(USER_PERFORMANCE_SORT_FIELDS)
        raise ValueError(f"sort_by must be one of: {allowed}")

    normalized_sort_dir = sort_dir.strip().lower()
    if normalized_sort_dir not in USER_PERFORMANCE_SORT_DIRECTIONS:
        raise ValueError("sort_dir must be asc or desc")

    filters = _build_event_filters(date_from=date_from, date_to=date_to)

    stmt = (
        select(
            User.id.label("user_id"),
            User.email.label("email"),
            func.max(_event_time_expr()).label("last_activity_at"),
            func.count(UserActivityEvent.id).label("total_activity_count"),
            _count_for_kind(ACTIVITY_KIND_READING_SESSION).label(
                "reading_sessions_count"
            ),
            _duration_sum_for_kind(ACTIVITY_KIND_READING_SESSION).label(
                "reading_total_duration_sec"
            ),
            _count_for_kind(ACTIVITY_KIND_REVIEW_THEORY).label("review_theory_count"),
            _avg_for_kind(
                ACTIVITY_KIND_REVIEW_THEORY,
                UserActivityEvent.rating_1_to_5,
            ).label("review_theory_avg_rating"),
            _avg_for_kind(
                ACTIVITY_KIND_REVIEW_THEORY,
                UserActivityEvent.score_0_to_100,
            ).label("review_theory_avg_score"),
            _count_for_kind(ACTIVITY_KIND_REVIEW_ALGORITHM_THEORY).label(
                "review_algorithm_theory_count"
            ),
            _avg_for_kind(
                ACTIVITY_KIND_REVIEW_ALGORITHM_THEORY,
                UserActivityEvent.rating_1_to_5,
            ).label("review_algorithm_theory_avg_rating"),
            _count_for_kind(ACTIVITY_KIND_ALGORITHM_TRAINING_TYPING).label(
                "training_typing_count"
            ),
            _duration_sum_for_kind(ACTIVITY_KIND_ALGORITHM_TRAINING_TYPING).label(
                "training_typing_total_duration_sec"
            ),
            _count_for_kind(ACTIVITY_KIND_ALGORITHM_TRAINING_MEMORY).label(
                "training_memory_count"
            ),
            _duration_sum_for_kind(ACTIVITY_KIND_ALGORITHM_TRAINING_MEMORY).label(
                "training_memory_total_duration_sec"
            ),
        )
        .join(User, User.id == UserActivityEvent.user_id)
        .where(*filters)
    )

    if search:
        normalized_search = f"%{search.strip().lower()}%"
        stmt = stmt.where(User.email.ilike(normalized_search))

    aggregated = stmt.group_by(User.id, User.email).subquery()

    sort_expr_map = {
        "last_activity_at": aggregated.c.last_activity_at,
        "reading_sessions": aggregated.c.reading_sessions_count,
        "total_activity_count": aggregated.c.total_activity_count,
    }
    sort_column = sort_expr_map[normalized_sort_by]
    sort_expression = (
        sort_column.asc()
        if normalized_sort_dir == "asc"
        else sort_column.desc()
    )

    rows = session.execute(
        select(aggregated)
        .order_by(sort_expression, aggregated.c.user_id.asc())
        .limit(limit)
        .offset(offset)
    ).mappings().all()

    total = session.execute(
        select(func.count()).select_from(aggregated)
    ).scalar_one()

    items = [
        {
            "user_id": row["user_id"],
            "email": row["email"],
            "name": None,
            "last_activity_at": row["last_activity_at"],
            "total_activity_count": _to_int(row["total_activity_count"]),
            "reading_sessions_count": _to_int(row["reading_sessions_count"]),
            "reading_total_duration_sec": _to_int(row["reading_total_duration_sec"]),
            "review_theory_count": _to_int(row["review_theory_count"]),
            "review_theory_avg_rating": _to_float(row["review_theory_avg_rating"]),
            "review_theory_avg_score": _to_float(row["review_theory_avg_score"]),
            "review_algorithm_theory_count": _to_int(
                row["review_algorithm_theory_count"]
            ),
            "review_algorithm_theory_avg_rating": _to_float(
                row["review_algorithm_theory_avg_rating"]
            ),
            "training_typing_count": _to_int(row["training_typing_count"]),
            "training_typing_total_duration_sec": _to_int(
                row["training_typing_total_duration_sec"]
            ),
            "training_memory_count": _to_int(row["training_memory_count"]),
            "training_memory_total_duration_sec": _to_int(
                row["training_memory_total_duration_sec"]
            ),
        }
        for row in rows
    ]
    return items, _to_int(total)


def get_user_performance(
    session: Session,
    *,
    user_id: UUID,
    date_from: date | None,
    date_to: date | None,
) -> dict[str, Any]:
    """Return aggregated performance summary for a single user."""
    filters = _build_event_filters(
        user_id=user_id,
        date_from=date_from,
        date_to=date_to,
    )

    row = session.execute(
        select(
            func.max(_event_time_expr()).label("last_activity_at"),
            func.count(UserActivityEvent.id).label("total_activity_count"),
            _count_for_kind(ACTIVITY_KIND_READING_SESSION).label(
                "reading_sessions_count"
            ),
            _duration_sum_for_kind(ACTIVITY_KIND_READING_SESSION).label(
                "reading_total_duration_sec"
            ),
            _avg_for_kind(
                ACTIVITY_KIND_READING_SESSION,
                UserActivityEvent.duration_sec,
            ).label("reading_avg_duration_sec"),
            _count_for_kind(ACTIVITY_KIND_REVIEW_THEORY).label("review_theory_count"),
            _avg_for_kind(
                ACTIVITY_KIND_REVIEW_THEORY,
                UserActivityEvent.rating_1_to_5,
            ).label("review_theory_avg_rating"),
            _avg_for_kind(
                ACTIVITY_KIND_REVIEW_THEORY,
                UserActivityEvent.score_0_to_100,
            ).label("review_theory_avg_score"),
            _last_value_subquery(
                user_id=user_id,
                activity_kind=ACTIVITY_KIND_REVIEW_THEORY,
                value_column=UserActivityEvent.rating_1_to_5,
                date_from=date_from,
                date_to=date_to,
            ).label("review_theory_last_rating"),
            _last_value_subquery(
                user_id=user_id,
                activity_kind=ACTIVITY_KIND_REVIEW_THEORY,
                value_column=UserActivityEvent.score_0_to_100,
                date_from=date_from,
                date_to=date_to,
            ).label("review_theory_last_score"),
            _count_for_kind(ACTIVITY_KIND_REVIEW_ALGORITHM_THEORY).label(
                "review_algorithm_theory_count"
            ),
            _avg_for_kind(
                ACTIVITY_KIND_REVIEW_ALGORITHM_THEORY,
                UserActivityEvent.rating_1_to_5,
            ).label("review_algorithm_theory_avg_rating"),
            _last_value_subquery(
                user_id=user_id,
                activity_kind=ACTIVITY_KIND_REVIEW_ALGORITHM_THEORY,
                value_column=UserActivityEvent.rating_1_to_5,
                date_from=date_from,
                date_to=date_to,
            ).label("review_algorithm_theory_last_rating"),
            _count_for_kind(ACTIVITY_KIND_ALGORITHM_TRAINING_TYPING).label(
                "training_typing_count"
            ),
            _duration_sum_for_kind(ACTIVITY_KIND_ALGORITHM_TRAINING_TYPING).label(
                "training_typing_total_duration_sec"
            ),
            _avg_for_kind(
                ACTIVITY_KIND_ALGORITHM_TRAINING_TYPING,
                UserActivityEvent.duration_sec,
            ).label("training_typing_avg_duration_sec"),
            _avg_for_kind(
                ACTIVITY_KIND_ALGORITHM_TRAINING_TYPING,
                UserActivityEvent.accuracy,
            ).label("training_typing_avg_accuracy"),
            _avg_for_kind(
                ACTIVITY_KIND_ALGORITHM_TRAINING_TYPING,
                UserActivityEvent.rating_1_to_5,
            ).label("training_typing_avg_rating"),
            _count_for_kind(ACTIVITY_KIND_ALGORITHM_TRAINING_MEMORY).label(
                "training_memory_count"
            ),
            _duration_sum_for_kind(ACTIVITY_KIND_ALGORITHM_TRAINING_MEMORY).label(
                "training_memory_total_duration_sec"
            ),
            _avg_for_kind(
                ACTIVITY_KIND_ALGORITHM_TRAINING_MEMORY,
                UserActivityEvent.duration_sec,
            ).label("training_memory_avg_duration_sec"),
            _avg_for_kind(
                ACTIVITY_KIND_ALGORITHM_TRAINING_MEMORY,
                UserActivityEvent.rating_1_to_5,
            ).label("training_memory_avg_rating"),
        ).where(*filters)
    ).mappings().one()

    return {
        "last_activity_at": row["last_activity_at"],
        "total_activity_count": _to_int(row["total_activity_count"]),
        "reading": {
            "sessions_count": _to_int(row["reading_sessions_count"]),
            "total_duration_sec": _to_int(row["reading_total_duration_sec"]),
            "avg_duration_sec": _to_float(row["reading_avg_duration_sec"]),
        },
        "review_theory": {
            "attempts_count": _to_int(row["review_theory_count"]),
            "avg_rating": _to_float(row["review_theory_avg_rating"]),
            "avg_score": _to_float(row["review_theory_avg_score"]),
            "last_rating": _to_float(row["review_theory_last_rating"]),
            "last_score": _to_float(row["review_theory_last_score"]),
        },
        "review_algorithm_theory": {
            "attempts_count": _to_int(row["review_algorithm_theory_count"]),
            "avg_rating": _to_float(row["review_algorithm_theory_avg_rating"]),
            "last_rating": _to_float(row["review_algorithm_theory_last_rating"]),
        },
        "training_typing": {
            "attempts_count": _to_int(row["training_typing_count"]),
            "total_duration_sec": _to_int(row["training_typing_total_duration_sec"]),
            "avg_duration_sec": _to_float(row["training_typing_avg_duration_sec"]),
            "avg_accuracy": _to_float(row["training_typing_avg_accuracy"]),
            "avg_rating": _to_float(row["training_typing_avg_rating"]),
        },
        "training_memory": {
            "attempts_count": _to_int(row["training_memory_count"]),
            "total_duration_sec": _to_int(row["training_memory_total_duration_sec"]),
            "avg_duration_sec": _to_float(row["training_memory_avg_duration_sec"]),
            "avg_rating": _to_float(row["training_memory_avg_rating"]),
        },
    }


def list_user_activity_events(
    session: Session,
    *,
    user_id: UUID,
    activity_kind: str | None,
    date_from: date | None,
    date_to: date | None,
    limit: int,
    offset: int,
) -> tuple[list[dict[str, Any]], int]:
    """List raw user activity events for admin timelines."""
    if activity_kind is not None and activity_kind not in USER_ACTIVITY_KINDS:
        allowed = ", ".join(USER_ACTIVITY_KINDS)
        raise ValueError(f"activity_kind must be one of: {allowed}")

    filters = _build_event_filters(
        user_id=user_id,
        activity_kind=activity_kind,
        date_from=date_from,
        date_to=date_to,
    )

    total = session.execute(
        select(func.count(UserActivityEvent.id)).where(*filters)
    ).scalar_one()

    items = (
        session.execute(
            select(UserActivityEvent)
            .where(*filters)
            .order_by(_event_time_expr().desc(), UserActivityEvent.id.desc())
            .limit(limit)
            .offset(offset)
        )
        .scalars()
        .all()
    )

    reading_part_ids = {
        item.reading_part_id
        for item in items
        if item.reading_part_id is not None
    }
    part_rows = session.execute(
        select(
            ReadingPart.id,
            ReadingPart.book_id,
            ReadingPart.label,
            ReadingPart.part_index,
        ).where(ReadingPart.id.in_(reading_part_ids))
    ).all()
    part_map = {
        row.id: {
            "book_id": row.book_id,
            "label": row.label,
            "part_index": row.part_index,
        }
        for row in part_rows
    }

    book_ids = {
        item.book_id
        for item in items
        if item.book_id is not None
    }
    book_ids.update(
        part["book_id"]
        for part in part_map.values()
        if part.get("book_id") is not None
    )
    book_title_map = {
        row.id: row.title
        for row in session.execute(
            select(Book.id, Book.title).where(Book.id.in_(book_ids))
        )
    }

    algorithm_ids = {
        item.algorithm_id
        for item in items
        if item.algorithm_id is not None
    }
    algorithm_title_map = {
        row.id: row.title
        for row in session.execute(
            select(Algorithm.id, Algorithm.title).where(
                Algorithm.id.in_(algorithm_ids)
            )
        )
    }

    payload: list[dict[str, Any]] = []
    for item in items:
        part_details = (
            part_map.get(item.reading_part_id)
            if item.reading_part_id is not None
            else None
        )
        resolved_book_id = item.book_id
        if resolved_book_id is None and part_details is not None:
            resolved_book_id = part_details.get("book_id")

        payload.append(
            {
                "id": item.id,
                "activity_kind": item.activity_kind,
                "status": item.status,
                "source": item.source,
                "created_at": item.created_at,
                "started_at": item.started_at,
                "ended_at": item.ended_at,
                "duration_sec": item.duration_sec,
                "score_0_to_100": item.score_0_to_100,
                "rating_1_to_5": item.rating_1_to_5,
                "result_label": item.result_label,
                "accuracy": item.accuracy,
                "book_id": item.book_id,
                "book_title": book_title_map.get(resolved_book_id),
                "reading_part_id": item.reading_part_id,
                "reading_part_label": part_details.get("label")
                if part_details is not None
                else None,
                "reading_part_index": part_details.get("part_index")
                if part_details is not None
                else None,
                "review_item_id": item.review_item_id,
                "algorithm_id": item.algorithm_id,
                "algorithm_title": algorithm_title_map.get(item.algorithm_id),
                "algorithm_review_item_id": item.algorithm_review_item_id,
                "algorithm_training_attempt_id": item.algorithm_training_attempt_id,
                "review_attempt_id": item.review_attempt_id,
                "algorithm_review_attempt_id": item.algorithm_review_attempt_id,
                "meta_json": item.meta_json,
            }
        )

    return payload, _to_int(total)
