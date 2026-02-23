"""Profile export service (portable JSON ZIP)."""

from __future__ import annotations

import hashlib
import json
from datetime import date, datetime, timezone
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any, Callable
from zipfile import ZIP_DEFLATED, ZipFile

from sqlalchemy import select
from sqlalchemy.orm import Session

from studying_light.db.models.algorithm import Algorithm
from studying_light.db.models.algorithm_code_snippet import AlgorithmCodeSnippet
from studying_light.db.models.algorithm_group import AlgorithmGroup
from studying_light.db.models.algorithm_review_attempt import AlgorithmReviewAttempt
from studying_light.db.models.algorithm_review_item import AlgorithmReviewItem
from studying_light.db.models.algorithm_training_attempt import AlgorithmTrainingAttempt
from studying_light.db.models.book import Book
from studying_light.db.models.reading_part import ReadingPart
from studying_light.db.models.review_attempt import ReviewAttempt
from studying_light.db.models.review_schedule_item import ReviewScheduleItem
from studying_light.db.models.user import User
from studying_light.db.models.user_settings import UserSettings

PROFILE_FORMAT = "studying-light-profile"
PROFILE_FORMAT_VERSION = 1
JSON_SEPARATORS = (",", ":")


def _app_version() -> str:
    try:
        return version("studying-light")
    except PackageNotFoundError:
        return "unknown"


def _jsonify(value: Any) -> Any:
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc).isoformat()
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, list):
        return [_jsonify(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _jsonify(item) for key, item in value.items()}
    return value


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def _write_json_array(
    path: Path,
    rows: list[dict[str, Any]],
) -> int:
    """Write rows into JSON array file and return written count."""
    with path.open("w", encoding="utf-8") as handle:
        handle.write("[")
        for index, row in enumerate(rows):
            if index:
                handle.write(",")
            handle.write(
                json.dumps(
                    row,
                    ensure_ascii=False,
                    separators=JSON_SEPARATORS,
                )
            )
        handle.write("]")
    return len(rows)


def _books_rows(session: Session, user: User) -> list[dict[str, Any]]:
    books = (
        session.execute(select(Book).where(Book.user_id == user.id).order_by(Book.id))
        .scalars()
        .all()
    )
    return [
        {
            "legacy_id": book.id,
            "user_id": str(book.user_id),
            "title": book.title,
            "author": book.author,
            "status": book.status,
            "pages_total": book.pages_total,
        }
        for book in books
    ]


def _reading_parts_rows(session: Session, user: User) -> list[dict[str, Any]]:
    parts = (
        session.execute(
            select(ReadingPart)
            .where(ReadingPart.user_id == user.id)
            .order_by(ReadingPart.id)
        )
        .scalars()
        .all()
    )
    return [
        {
            "legacy_id": part.id,
            "user_id": str(part.user_id),
            "book_legacy_id": part.book_id,
            "part_index": part.part_index,
            "label": part.label,
            "created_at": _jsonify(part.created_at),
            "raw_notes": _jsonify(part.raw_notes),
            "gpt_summary": part.gpt_summary,
            "gpt_questions_by_interval": _jsonify(part.gpt_questions_by_interval),
            "pages_read": part.pages_read,
            "session_seconds": part.session_seconds,
            "page_end": part.page_end,
        }
        for part in parts
    ]


def _review_items_rows(session: Session, user: User) -> list[dict[str, Any]]:
    items = (
        session.execute(
            select(ReviewScheduleItem)
            .where(ReviewScheduleItem.user_id == user.id)
            .order_by(ReviewScheduleItem.id)
        )
        .scalars()
        .all()
    )
    return [
        {
            "legacy_id": item.id,
            "user_id": str(item.user_id),
            "reading_part_legacy_id": item.reading_part_id,
            "interval_days": item.interval_days,
            "due_date": _jsonify(item.due_date),
            "status": item.status,
            "completed_at": _jsonify(item.completed_at),
            "questions": _jsonify(item.questions),
        }
        for item in items
    ]


def _review_attempts_rows(session: Session, user: User) -> list[dict[str, Any]]:
    attempts = (
        session.execute(
            select(ReviewAttempt)
            .where(ReviewAttempt.user_id == user.id)
            .order_by(ReviewAttempt.id)
        )
        .scalars()
        .all()
    )
    return [
        {
            "legacy_id": attempt.id,
            "user_id": str(attempt.user_id),
            "review_item_legacy_id": attempt.review_item_id,
            "answers": _jsonify(attempt.answers),
            "created_at": _jsonify(attempt.created_at),
            "gpt_check_result": attempt.gpt_check_result,
            "gpt_check_payload": _jsonify(attempt.gpt_check_payload),
            "gpt_rating_1_to_5": attempt.gpt_rating_1_to_5,
            "gpt_score_0_to_100": attempt.gpt_score_0_to_100,
            "gpt_verdict": attempt.gpt_verdict,
        }
        for attempt in attempts
    ]


def _algorithm_groups_rows(session: Session, user: User) -> list[dict[str, Any]]:
    groups = (
        session.execute(
            select(AlgorithmGroup)
            .where(AlgorithmGroup.user_id == user.id)
            .order_by(AlgorithmGroup.id)
        )
        .scalars()
        .all()
    )
    return [
        {
            "legacy_id": group.id,
            "user_id": str(group.user_id),
            "title": group.title,
            "title_norm": group.title_norm,
            "description": group.description,
            "notes": group.notes,
            "created_at": _jsonify(group.created_at),
            "updated_at": _jsonify(group.updated_at),
        }
        for group in groups
    ]


def _algorithms_rows(session: Session, user: User) -> list[dict[str, Any]]:
    algorithms = (
        session.execute(
            select(Algorithm).where(Algorithm.user_id == user.id).order_by(Algorithm.id)
        )
        .scalars()
        .all()
    )
    return [
        {
            "legacy_id": algorithm.id,
            "user_id": str(algorithm.user_id),
            "group_legacy_id": algorithm.group_id,
            "source_part_legacy_id": algorithm.source_part_id,
            "title": algorithm.title,
            "summary": algorithm.summary,
            "when_to_use": algorithm.when_to_use,
            "complexity": algorithm.complexity,
            "invariants": _jsonify(algorithm.invariants),
            "steps": _jsonify(algorithm.steps),
            "corner_cases": _jsonify(algorithm.corner_cases),
            "created_at": _jsonify(algorithm.created_at),
            "updated_at": _jsonify(algorithm.updated_at),
        }
        for algorithm in algorithms
    ]


def _algorithm_code_snippets_rows(session: Session, user: User) -> list[dict[str, Any]]:
    snippets = (
        session.execute(
            select(AlgorithmCodeSnippet)
            .where(AlgorithmCodeSnippet.user_id == user.id)
            .order_by(AlgorithmCodeSnippet.id)
        )
        .scalars()
        .all()
    )
    return [
        {
            "legacy_id": snippet.id,
            "user_id": str(snippet.user_id),
            "algorithm_legacy_id": snippet.algorithm_id,
            "code_kind": snippet.code_kind,
            "language": snippet.language,
            "code_text": snippet.code_text,
            "is_reference": snippet.is_reference,
            "created_at": _jsonify(snippet.created_at),
        }
        for snippet in snippets
    ]


def _algorithm_review_items_rows(session: Session, user: User) -> list[dict[str, Any]]:
    items = (
        session.execute(
            select(AlgorithmReviewItem)
            .where(AlgorithmReviewItem.user_id == user.id)
            .order_by(AlgorithmReviewItem.id)
        )
        .scalars()
        .all()
    )
    return [
        {
            "legacy_id": item.id,
            "user_id": str(item.user_id),
            "algorithm_legacy_id": item.algorithm_id,
            "interval_days": item.interval_days,
            "due_date": _jsonify(item.due_date),
            "status": item.status,
            "completed_at": _jsonify(item.completed_at),
            "questions": _jsonify(item.questions),
        }
        for item in items
    ]


def _algorithm_review_attempts_rows(
    session: Session,
    user: User,
) -> list[dict[str, Any]]:
    attempts = (
        session.execute(
            select(AlgorithmReviewAttempt)
            .where(AlgorithmReviewAttempt.user_id == user.id)
            .order_by(AlgorithmReviewAttempt.id)
        )
        .scalars()
        .all()
    )
    return [
        {
            "legacy_id": attempt.id,
            "user_id": str(attempt.user_id),
            "review_item_legacy_id": attempt.review_item_id,
            "answers": _jsonify(attempt.answers),
            "gpt_check_json": _jsonify(attempt.gpt_check_json),
            "rating_1_to_5": attempt.rating_1_to_5,
            "created_at": _jsonify(attempt.created_at),
        }
        for attempt in attempts
    ]


def _algorithm_training_attempts_rows(
    session: Session,
    user: User,
) -> list[dict[str, Any]]:
    attempts = (
        session.execute(
            select(AlgorithmTrainingAttempt)
            .where(AlgorithmTrainingAttempt.user_id == user.id)
            .order_by(AlgorithmTrainingAttempt.id)
        )
        .scalars()
        .all()
    )
    return [
        {
            "legacy_id": attempt.id,
            "user_id": str(attempt.user_id),
            "algorithm_legacy_id": attempt.algorithm_id,
            "mode": attempt.mode,
            "code_text": attempt.code_text,
            "gpt_check_json": _jsonify(attempt.gpt_check_json),
            "rating_1_to_5": attempt.rating_1_to_5,
            "accuracy": attempt.accuracy,
            "duration_sec": attempt.duration_sec,
            "created_at": _jsonify(attempt.created_at),
        }
        for attempt in attempts
    ]


def _user_settings_rows(session: Session, user: User) -> list[dict[str, Any]]:
    settings = session.get(UserSettings, user.id)
    if not settings:
        return []
    return [
        {
            "legacy_id": str(settings.user_id),
            "user_id": str(settings.user_id),
            "timezone": settings.timezone,
            "pomodoro_work_min": settings.pomodoro_work_min,
            "pomodoro_break_min": settings.pomodoro_break_min,
            "daily_goal_weekday_min": settings.daily_goal_weekday_min,
            "daily_goal_weekend_min": settings.daily_goal_weekend_min,
            "intervals_days": _jsonify(settings.intervals_days),
        }
    ]


RowBuilder = Callable[[Session, User], list[dict[str, Any]]]

DATA_BUILDERS: dict[str, tuple[str, RowBuilder, bool]] = {
    "data/books.json": ("books", _books_rows, True),
    "data/reading_parts.json": ("reading_parts", _reading_parts_rows, True),
    "data/review_schedule_items.json": (
        "review_schedule_items",
        _review_items_rows,
        True,
    ),
    "data/review_attempts.json": ("review_attempts", _review_attempts_rows, True),
    "data/algorithm_groups.json": (
        "algorithm_groups",
        _algorithm_groups_rows,
        True,
    ),
    "data/algorithms.json": ("algorithms", _algorithms_rows, True),
    "data/algorithm_code_snippets.json": (
        "algorithm_code_snippets",
        _algorithm_code_snippets_rows,
        True,
    ),
    "data/algorithm_review_items.json": (
        "algorithm_review_items",
        _algorithm_review_items_rows,
        True,
    ),
    "data/algorithm_review_attempts.json": (
        "algorithm_review_attempts",
        _algorithm_review_attempts_rows,
        True,
    ),
    "data/algorithm_training_attempts.json": (
        "algorithm_training_attempts",
        _algorithm_training_attempts_rows,
        True,
    ),
    "data/user_settings.json": ("user_settings", _user_settings_rows, False),
}


def export_profile_zip_to_file(session: Session, user: User, zip_path: Path) -> None:
    """Build a ZIP archive with profile JSON files and manifest on disk."""
    data_dir = zip_path.parent / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    counts: dict[str, int] = {}
    checksums: dict[str, str] = {}
    data_files: list[str] = []
    interval_days_snapshot: list[int] | None = None

    for file_name, (count_key, builder, always_include) in DATA_BUILDERS.items():
        rows = builder(session, user)
        counts[count_key] = len(rows)
        if not rows and not always_include:
            continue

        file_path = zip_path.parent / file_name
        file_path.parent.mkdir(parents=True, exist_ok=True)
        _write_json_array(file_path, rows)

        checksums[file_name] = _hash_file(file_path)
        data_files.append(file_name)

        if file_name == "data/user_settings.json" and rows:
            interval_days_snapshot = rows[0].get("intervals_days")

    manifest: dict[str, Any] = {
        "format": PROFILE_FORMAT,
        "format_version": PROFILE_FORMAT_VERSION,
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "app_version": _app_version(),
        "counts": counts,
        "sha256": checksums,
        "data_files": data_files,
    }
    if interval_days_snapshot is not None:
        manifest["intervals_days"] = interval_days_snapshot

    manifest_path = zip_path.parent / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, separators=JSON_SEPARATORS),
        encoding="utf-8",
    )

    with ZipFile(zip_path, "w", ZIP_DEFLATED) as archive:
        archive.write(manifest_path, "manifest.json")
        for file_name in data_files:
            archive.write(zip_path.parent / file_name, file_name)
