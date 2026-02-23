"""Backfill historical user activity events from domain tables."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
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
from studying_light.db.models.algorithm_review_attempt import AlgorithmReviewAttempt
from studying_light.db.models.algorithm_review_item import AlgorithmReviewItem
from studying_light.db.models.algorithm_training_attempt import AlgorithmTrainingAttempt
from studying_light.db.models.reading_part import ReadingPart
from studying_light.db.models.review_attempt import ReviewAttempt
from studying_light.db.models.review_schedule_item import ReviewScheduleItem
from studying_light.db.models.user_activity_event import UserActivityEvent

TRAINING_MODE_TO_ACTIVITY_KIND: dict[str, str] = {
    "typing": ACTIVITY_KIND_ALGORITHM_TRAINING_TYPING,
    "memory": ACTIVITY_KIND_ALGORITHM_TRAINING_MEMORY,
}

GROUP_READING = "reading"
GROUP_REVIEW_THEORY = "review_theory"
GROUP_REVIEW_ALGORITHM = "review_algorithm_theory"
GROUP_TRAINING = "algorithm_training"


@dataclass(slots=True)
class BackfillGroupStats:
    """Counters for one backfill activity group."""

    scanned: int = 0
    created: int = 0
    skipped_duplicates: int = 0
    skipped_invalid: int = 0
    errors: int = 0

    def to_dict(self) -> dict[str, int]:
        return {
            "scanned": self.scanned,
            "created": self.created,
            "skipped_duplicates": self.skipped_duplicates,
            "skipped_invalid": self.skipped_invalid,
            "errors": self.errors,
        }


@dataclass(slots=True)
class BackfillReport:
    """Backfill summary by activity group."""

    groups: dict[str, BackfillGroupStats] = field(default_factory=dict)

    @property
    def total(self) -> BackfillGroupStats:
        total = BackfillGroupStats()
        for group in self.groups.values():
            total.scanned += group.scanned
            total.created += group.created
            total.skipped_duplicates += group.skipped_duplicates
            total.skipped_invalid += group.skipped_invalid
            total.errors += group.errors
        return total

    def to_dict(self) -> dict[str, dict[str, int]]:
        payload = {name: group.to_dict() for name, group in self.groups.items()}
        payload["total"] = self.total.to_dict()
        return payload


def _existing_ref_ids(
    session: Session,
    *,
    activity_kind: str,
    column,
) -> set[int]:
    rows = session.execute(
        select(column).where(
            UserActivityEvent.activity_kind == activity_kind,
            column.is_not(None),
        )
    ).scalars()
    return {int(value) for value in rows}


def _safe_duration(duration_sec: int | None, stats: BackfillGroupStats) -> int | None:
    if duration_sec is None:
        return None
    if duration_sec < 0:
        stats.skipped_invalid += 1
        return None
    return int(duration_sec)


def _find_duplicate_event(
    session: Session,
    *,
    event: UserActivityEvent,
) -> UserActivityEvent | None:
    if event.reading_part_id is not None:
        ref_filter = UserActivityEvent.reading_part_id == event.reading_part_id
    elif event.review_attempt_id is not None:
        ref_filter = UserActivityEvent.review_attempt_id == event.review_attempt_id
    elif event.algorithm_review_attempt_id is not None:
        ref_filter = (
            UserActivityEvent.algorithm_review_attempt_id
            == event.algorithm_review_attempt_id
        )
    elif event.algorithm_training_attempt_id is not None:
        ref_filter = (
            UserActivityEvent.algorithm_training_attempt_id
            == event.algorithm_training_attempt_id
        )
    else:
        return None

    return session.execute(
        select(UserActivityEvent)
        .where(
            UserActivityEvent.activity_kind == event.activity_kind,
            ref_filter,
        )
        .order_by(UserActivityEvent.id.desc())
        .limit(1)
    ).scalar_one_or_none()


def _persist_event(
    session: Session,
    *,
    event: UserActivityEvent,
    stats: BackfillGroupStats,
    dry_run: bool,
) -> bool:
    if dry_run:
        stats.created += 1
        return True

    try:
        with session.begin_nested():
            session.add(event)
            session.flush()
    except IntegrityError:
        duplicate = _find_duplicate_event(session, event=event)
        if duplicate is not None:
            stats.skipped_duplicates += 1
            return False
        stats.errors += 1
        return False
    except SQLAlchemyError:
        stats.errors += 1
        return False

    stats.created += 1
    return True


def _maybe_commit_batch(
    session: Session,
    *,
    dry_run: bool,
    pending_inserts: int,
    batch_size: int,
) -> int:
    if dry_run:
        return 0
    if pending_inserts < batch_size:
        return pending_inserts
    session.commit()
    return 0


def _finalize_group(
    session: Session,
    *,
    dry_run: bool,
    pending_inserts: int,
) -> None:
    if dry_run:
        return
    if pending_inserts > 0:
        session.commit()


def _backfill_reading(
    session: Session,
    *,
    dry_run: bool,
    batch_size: int,
) -> BackfillGroupStats:
    stats = BackfillGroupStats()
    existing_reading_part_ids = _existing_ref_ids(
        session,
        activity_kind=ACTIVITY_KIND_READING_SESSION,
        column=UserActivityEvent.reading_part_id,
    )

    pending_inserts = 0
    parts = session.execute(select(ReadingPart).order_by(ReadingPart.id)).scalars()
    for part in parts:
        stats.scanned += 1
        if part.id in existing_reading_part_ids:
            stats.skipped_duplicates += 1
            continue

        duration_sec = _safe_duration(part.session_seconds, stats)
        ended_at = part.created_at
        started_at = None
        if ended_at is not None and duration_sec is not None:
            started_at = ended_at - timedelta(seconds=duration_sec)

        event = UserActivityEvent(
            user_id=part.user_id,
            activity_kind=ACTIVITY_KIND_READING_SESSION,
            status=ACTIVITY_STATUS_COMPLETED,
            source=ACTIVITY_SOURCE_BACKFILL,
            created_at=ended_at or part.created_at,
            started_at=started_at,
            ended_at=ended_at,
            duration_sec=duration_sec,
            book_id=part.book_id,
            reading_part_id=part.id,
            meta_json={"pages_read": part.pages_read, "page_end": part.page_end},
        )
        if not _persist_event(
            session,
            event=event,
            stats=stats,
            dry_run=dry_run,
        ):
            continue

        existing_reading_part_ids.add(part.id)
        pending_inserts += 1
        pending_inserts = _maybe_commit_batch(
            session,
            dry_run=dry_run,
            pending_inserts=pending_inserts,
            batch_size=batch_size,
        )

    _finalize_group(session, dry_run=dry_run, pending_inserts=pending_inserts)
    return stats


def _backfill_review_theory(
    session: Session,
    *,
    dry_run: bool,
    batch_size: int,
) -> BackfillGroupStats:
    stats = BackfillGroupStats()
    existing_review_attempt_ids = _existing_ref_ids(
        session,
        activity_kind=ACTIVITY_KIND_REVIEW_THEORY,
        column=UserActivityEvent.review_attempt_id,
    )

    pending_inserts = 0
    rows = session.execute(
        select(ReviewAttempt, ReviewScheduleItem)
        .outerjoin(
            ReviewScheduleItem,
            ReviewAttempt.review_item_id == ReviewScheduleItem.id,
        )
        .order_by(ReviewAttempt.id)
    )
    for attempt, review_item in rows:
        stats.scanned += 1
        if attempt.id in existing_review_attempt_ids:
            stats.skipped_duplicates += 1
            continue

        if review_item is None:
            stats.errors += 1
            continue
        if review_item.user_id != attempt.user_id:
            stats.errors += 1
            continue

        ended_at = review_item.completed_at or attempt.created_at
        event = UserActivityEvent(
            user_id=attempt.user_id,
            activity_kind=ACTIVITY_KIND_REVIEW_THEORY,
            status=ACTIVITY_STATUS_COMPLETED,
            source=ACTIVITY_SOURCE_BACKFILL,
            created_at=ended_at or attempt.created_at,
            started_at=attempt.created_at,
            ended_at=ended_at,
            duration_sec=None,
            score_0_to_100=attempt.gpt_score_0_to_100,
            rating_1_to_5=attempt.gpt_rating_1_to_5,
            result_label=attempt.gpt_verdict,
            reading_part_id=review_item.reading_part_id,
            review_item_id=review_item.id,
            review_attempt_id=attempt.id,
        )
        if not _persist_event(
            session,
            event=event,
            stats=stats,
            dry_run=dry_run,
        ):
            continue

        existing_review_attempt_ids.add(attempt.id)
        pending_inserts += 1
        pending_inserts = _maybe_commit_batch(
            session,
            dry_run=dry_run,
            pending_inserts=pending_inserts,
            batch_size=batch_size,
        )

    _finalize_group(session, dry_run=dry_run, pending_inserts=pending_inserts)
    return stats


def _backfill_review_algorithm_theory(
    session: Session,
    *,
    dry_run: bool,
    batch_size: int,
) -> BackfillGroupStats:
    stats = BackfillGroupStats()
    existing_algorithm_review_attempt_ids = _existing_ref_ids(
        session,
        activity_kind=ACTIVITY_KIND_REVIEW_ALGORITHM_THEORY,
        column=UserActivityEvent.algorithm_review_attempt_id,
    )

    pending_inserts = 0
    rows = session.execute(
        select(AlgorithmReviewAttempt, AlgorithmReviewItem)
        .outerjoin(
            AlgorithmReviewItem,
            AlgorithmReviewAttempt.review_item_id == AlgorithmReviewItem.id,
        )
        .order_by(AlgorithmReviewAttempt.id)
    )
    for attempt, review_item in rows:
        stats.scanned += 1
        if attempt.id in existing_algorithm_review_attempt_ids:
            stats.skipped_duplicates += 1
            continue

        if review_item is None:
            stats.errors += 1
            continue
        if review_item.user_id != attempt.user_id:
            stats.errors += 1
            continue

        ended_at = review_item.completed_at or attempt.created_at
        event = UserActivityEvent(
            user_id=attempt.user_id,
            activity_kind=ACTIVITY_KIND_REVIEW_ALGORITHM_THEORY,
            status=ACTIVITY_STATUS_COMPLETED,
            source=ACTIVITY_SOURCE_BACKFILL,
            created_at=ended_at or attempt.created_at,
            started_at=attempt.created_at,
            ended_at=ended_at,
            duration_sec=None,
            rating_1_to_5=attempt.rating_1_to_5,
            algorithm_id=review_item.algorithm_id,
            algorithm_review_item_id=review_item.id,
            algorithm_review_attempt_id=attempt.id,
        )
        if not _persist_event(
            session,
            event=event,
            stats=stats,
            dry_run=dry_run,
        ):
            continue

        existing_algorithm_review_attempt_ids.add(attempt.id)
        pending_inserts += 1
        pending_inserts = _maybe_commit_batch(
            session,
            dry_run=dry_run,
            pending_inserts=pending_inserts,
            batch_size=batch_size,
        )

    _finalize_group(session, dry_run=dry_run, pending_inserts=pending_inserts)
    return stats


def _backfill_algorithm_training(
    session: Session,
    *,
    dry_run: bool,
    batch_size: int,
) -> BackfillGroupStats:
    stats = BackfillGroupStats()
    existing_training_event_keys = {
        (
            row.algorithm_training_attempt_id,
            row.activity_kind,
        )
        for row in session.execute(
            select(
                UserActivityEvent.algorithm_training_attempt_id,
                UserActivityEvent.activity_kind,
            ).where(
                UserActivityEvent.algorithm_training_attempt_id.is_not(None),
                UserActivityEvent.activity_kind.in_(
                    (
                        ACTIVITY_KIND_ALGORITHM_TRAINING_TYPING,
                        ACTIVITY_KIND_ALGORITHM_TRAINING_MEMORY,
                    )
                ),
            )
        )
    }

    pending_inserts = 0
    attempts = session.execute(
        select(AlgorithmTrainingAttempt).order_by(AlgorithmTrainingAttempt.id)
    ).scalars()
    for attempt in attempts:
        stats.scanned += 1
        activity_kind = TRAINING_MODE_TO_ACTIVITY_KIND.get(attempt.mode)
        if activity_kind is None:
            stats.skipped_invalid += 1
            continue

        dedupe_key = (attempt.id, activity_kind)
        if dedupe_key in existing_training_event_keys:
            stats.skipped_duplicates += 1
            continue

        duration_sec = _safe_duration(attempt.duration_sec, stats)
        ended_at = attempt.created_at
        started_at = None
        if ended_at is not None and duration_sec is not None:
            started_at = ended_at - timedelta(seconds=duration_sec)

        event = UserActivityEvent(
            user_id=attempt.user_id,
            activity_kind=activity_kind,
            status=ACTIVITY_STATUS_COMPLETED,
            source=ACTIVITY_SOURCE_BACKFILL,
            created_at=ended_at or attempt.created_at,
            started_at=started_at,
            ended_at=ended_at,
            duration_sec=duration_sec,
            rating_1_to_5=attempt.rating_1_to_5,
            accuracy=attempt.accuracy,
            algorithm_id=attempt.algorithm_id,
            algorithm_training_attempt_id=attempt.id,
            meta_json={"mode": attempt.mode},
        )
        if not _persist_event(
            session,
            event=event,
            stats=stats,
            dry_run=dry_run,
        ):
            continue

        existing_training_event_keys.add(dedupe_key)
        pending_inserts += 1
        pending_inserts = _maybe_commit_batch(
            session,
            dry_run=dry_run,
            pending_inserts=pending_inserts,
            batch_size=batch_size,
        )

    _finalize_group(session, dry_run=dry_run, pending_inserts=pending_inserts)
    return stats


def backfill_user_activity_events(
    session: Session,
    *,
    dry_run: bool = False,
    batch_size: int = 200,
) -> BackfillReport:
    """Backfill historical activity events from existing domain tables."""
    if batch_size <= 0:
        raise ValueError("batch_size must be positive")

    report = BackfillReport()
    report.groups[GROUP_READING] = _backfill_reading(
        session,
        dry_run=dry_run,
        batch_size=batch_size,
    )
    report.groups[GROUP_REVIEW_THEORY] = _backfill_review_theory(
        session,
        dry_run=dry_run,
        batch_size=batch_size,
    )
    report.groups[GROUP_REVIEW_ALGORITHM] = _backfill_review_algorithm_theory(
        session,
        dry_run=dry_run,
        batch_size=batch_size,
    )
    report.groups[GROUP_TRAINING] = _backfill_algorithm_training(
        session,
        dry_run=dry_run,
        batch_size=batch_size,
    )

    if dry_run:
        session.rollback()
    return report


def format_backfill_report(report: BackfillReport) -> str:
    """Render a compact CLI summary for a backfill report."""
    lines = ["Backfill summary:"]
    for group_name, stats in report.groups.items():
        lines.append(
            "  "
            f"{group_name}: "
            f"scanned={stats.scanned}, "
            f"created={stats.created}, "
            f"skipped_duplicates={stats.skipped_duplicates}, "
            f"skipped_invalid={stats.skipped_invalid}, "
            f"errors={stats.errors}"
        )
    total = report.total
    lines.append(
        "  "
        f"total: "
        f"scanned={total.scanned}, "
        f"created={total.created}, "
        f"skipped_duplicates={total.skipped_duplicates}, "
        f"skipped_invalid={total.skipped_invalid}, "
        f"errors={total.errors}"
    )
    return "\n".join(lines)
