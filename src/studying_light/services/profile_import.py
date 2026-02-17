"""Profile import service (portable JSON ZIP)."""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass
from datetime import date, datetime
from io import BytesIO
from pathlib import PurePosixPath
from typing import Any, Literal
from zipfile import BadZipFile, ZipFile

from pydantic import BaseModel, ConfigDict, ValidationError
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from studying_light.db.models.algorithm import Algorithm
from studying_light.db.models.algorithm_code_snippet import AlgorithmCodeSnippet
from studying_light.db.models.algorithm_group import (
    AlgorithmGroup,
    normalize_group_title,
)
from studying_light.db.models.algorithm_review_attempt import AlgorithmReviewAttempt
from studying_light.db.models.algorithm_review_item import AlgorithmReviewItem
from studying_light.db.models.algorithm_training_attempt import AlgorithmTrainingAttempt
from studying_light.db.models.book import Book
from studying_light.db.models.reading_part import ReadingPart
from studying_light.db.models.review_attempt import ReviewAttempt
from studying_light.db.models.review_schedule_item import ReviewScheduleItem
from studying_light.db.models.user import User
from studying_light.db.models.user_settings import UserSettings
from studying_light.services.profile_export import (
    PROFILE_FORMAT,
    PROFILE_FORMAT_VERSION,
)

ImportMode = Literal["merge", "replace"]

MAX_ARCHIVE_SIZE_BYTES = 200 * 1024 * 1024
MAX_TOTAL_EXTRACTED_SIZE_BYTES = 400 * 1024 * 1024

KNOWN_DATA_FILES: dict[str, str] = {
    "data/books.json": "books",
    "data/reading_parts.json": "reading_parts",
    "data/review_schedule_items.json": "review_schedule_items",
    "data/review_attempts.json": "review_attempts",
    "data/algorithm_groups.json": "algorithm_groups",
    "data/algorithms.json": "algorithms",
    "data/algorithm_code_snippets.json": "algorithm_code_snippets",
    "data/algorithm_review_items.json": "algorithm_review_items",
    "data/algorithm_review_attempts.json": "algorithm_review_attempts",
    "data/algorithm_training_attempts.json": "algorithm_training_attempts",
    "data/user_settings.json": "user_settings",
}

OPTIONAL_FILES = {"data/user_settings.json"}
MAX_ARCHIVE_FILES_COUNT = len(KNOWN_DATA_FILES) + 4
MERGE_WARNING_THRESHOLD = 10


@dataclass
class ProfileImportError(Exception):
    detail: str
    code: str
    errors: list[dict[str, Any]] | None = None
    status_code: int = 400

    def payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {"detail": self.detail, "code": self.code}
        if self.errors:
            payload["errors"] = self.errors
        return payload


class ManifestModel(BaseModel):
    model_config = ConfigDict(extra="ignore")

    format: str
    format_version: int
    exported_at: datetime
    app_version: str | None = None
    intervals_days: list[int] | None = None
    counts: dict[str, int] = {}
    sha256: dict[str, str]
    data_files: list[str] | None = None


class _ImportModel(BaseModel):
    model_config = ConfigDict(extra="ignore")


class BookIn(_ImportModel):
    legacy_id: int
    title: str
    author: str | None = None
    status: str = "active"
    pages_total: int | None = None


class ReadingPartIn(_ImportModel):
    legacy_id: int
    book_legacy_id: int
    part_index: int
    label: str | None = None
    created_at: datetime | None = None
    raw_notes: dict | None = None
    gpt_summary: str | None = None
    gpt_questions_by_interval: dict | None = None
    pages_read: int | None = None
    session_seconds: int | None = None
    page_end: int | None = None


class ReviewItemIn(_ImportModel):
    legacy_id: int
    reading_part_legacy_id: int
    interval_days: int
    due_date: date
    status: str = "planned"
    completed_at: datetime | None = None
    questions: list | None = None


class ReviewAttemptIn(_ImportModel):
    legacy_id: int
    review_item_legacy_id: int
    answers: dict | None = None
    created_at: datetime | None = None
    gpt_check_result: str | None = None
    gpt_check_payload: dict | None = None
    gpt_rating_1_to_5: int | None = None
    gpt_score_0_to_100: int | None = None
    gpt_verdict: str | None = None


class AlgorithmGroupIn(_ImportModel):
    legacy_id: int
    title: str
    description: str | None = None
    notes: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class AlgorithmIn(_ImportModel):
    legacy_id: int
    group_legacy_id: int
    source_part_legacy_id: int | None = None
    title: str
    summary: str
    when_to_use: str
    complexity: str
    invariants: list
    steps: list
    corner_cases: list
    created_at: datetime | None = None
    updated_at: datetime | None = None


class AlgorithmCodeSnippetIn(_ImportModel):
    legacy_id: int
    algorithm_legacy_id: int
    code_kind: str
    language: str
    code_text: str
    is_reference: bool = True
    created_at: datetime | None = None


class AlgorithmReviewItemIn(_ImportModel):
    legacy_id: int
    algorithm_legacy_id: int
    interval_days: int
    due_date: date
    status: str = "planned"
    completed_at: datetime | None = None
    questions: list | None = None


class AlgorithmReviewAttemptIn(_ImportModel):
    legacy_id: int
    review_item_legacy_id: int
    answers: dict | None = None
    gpt_check_json: dict | None = None
    rating_1_to_5: int | None = None
    created_at: datetime | None = None


class AlgorithmTrainingAttemptIn(_ImportModel):
    legacy_id: int
    algorithm_legacy_id: int
    mode: str = "memory"
    code_text: str
    gpt_check_json: dict | None = None
    rating_1_to_5: int | None = None
    accuracy: float | None = None
    duration_sec: int | None = None
    created_at: datetime | None = None


class UserSettingsIn(_ImportModel):
    legacy_id: str | int | None = None
    timezone: str | None = None
    pomodoro_work_min: int | None = None
    pomodoro_break_min: int | None = None
    daily_goal_weekday_min: int | None = None
    daily_goal_weekend_min: int | None = None
    intervals_days: list | None = None


def _raise_invalid(detail: str, errors: list[dict[str, Any]] | None = None) -> None:
    raise ProfileImportError(
        detail=detail,
        code="PROFILE_IMPORT_INVALID",
        errors=errors,
        status_code=400,
    )


def _raise_too_large(detail: str) -> None:
    raise ProfileImportError(
        detail=detail,
        code="PROFILE_IMPORT_TOO_LARGE",
        status_code=413,
    )


def _is_unsafe_zip_name(name: str) -> bool:
    normalized = name.replace("\\", "/")
    path = PurePosixPath(normalized)
    if normalized.startswith("/") or normalized.startswith("\\"):
        return True
    if path.is_absolute():
        return True
    if ".." in path.parts:
        return True
    return False


def _can_missing_file_be_empty(manifest: ManifestModel, file_name: str) -> bool:
    count_key = KNOWN_DATA_FILES[file_name]
    count = manifest.counts.get(count_key)
    return count in (None, 0)


def _load_zip(file_bytes: bytes) -> tuple[ManifestModel, dict[str, bytes]]:
    if len(file_bytes) > MAX_ARCHIVE_SIZE_BYTES:
        _raise_too_large("Archive exceeds maximum allowed size")

    try:
        archive = ZipFile(BytesIO(file_bytes))
    except BadZipFile as exc:
        raise ProfileImportError(
            detail="Invalid ZIP archive",
            code="PROFILE_IMPORT_CORRUPT",
            status_code=400,
        ) from exc

    with archive:
        infos = archive.infolist()
        if len(infos) > MAX_ARCHIVE_FILES_COUNT:
            _raise_too_large("Archive contains too many files")

        total_extracted_size = sum(info.file_size for info in infos)
        if total_extracted_size > MAX_TOTAL_EXTRACTED_SIZE_BYTES:
            _raise_too_large("Archive extracted size exceeds maximum allowed size")

        for info in infos:
            if _is_unsafe_zip_name(info.filename):
                raise ProfileImportError(
                    detail="Archive contains unsafe file path",
                    code="PROFILE_IMPORT_CORRUPT",
                    errors=[{"file": info.filename}],
                    status_code=400,
                )

        names = {info.filename for info in infos}
        if "manifest.json" not in names:
            _raise_invalid("manifest.json is required")

        try:
            manifest_data = json.loads(archive.read("manifest.json"))
            manifest = ManifestModel.model_validate(manifest_data)
        except (json.JSONDecodeError, ValidationError) as exc:
            raise ProfileImportError(
                detail="manifest.json is invalid",
                code="PROFILE_IMPORT_INVALID",
                errors=[{"msg": str(exc)}],
            ) from exc

        if manifest.format != PROFILE_FORMAT:
            _raise_invalid("Unsupported profile format")

        if manifest.format_version != PROFILE_FORMAT_VERSION:
            raise ProfileImportError(
                detail="Unsupported profile format version",
                code="PROFILE_IMPORT_UNSUPPORTED_VERSION",
                status_code=422,
            )

        if manifest.data_files is not None:
            missing_listed = sorted(
                file_name
                for file_name in manifest.data_files
                if file_name in KNOWN_DATA_FILES and file_name not in names
            )
            if missing_listed:
                _raise_invalid(
                    "Manifest data_files references missing files",
                    errors=[{"missing": missing_listed}],
                )

        missing_not_compatible = []
        for file_name in KNOWN_DATA_FILES:
            if file_name in names:
                continue
            if file_name in OPTIONAL_FILES and _can_missing_file_be_empty(
                manifest,
                file_name,
            ):
                continue
            if file_name in (manifest.data_files or []):
                missing_not_compatible.append(file_name)
                continue
            if not _can_missing_file_be_empty(manifest, file_name):
                missing_not_compatible.append(file_name)

        if missing_not_compatible:
            _raise_invalid(
                "Missing required files",
                errors=[{"missing": sorted(missing_not_compatible)}],
            )

        data_bytes: dict[str, bytes] = {}
        for file_name in KNOWN_DATA_FILES:
            if file_name in names:
                data_bytes[file_name] = archive.read(file_name)

        for file_name, raw in data_bytes.items():
            expected = manifest.sha256.get(file_name)
            if not expected:
                _raise_invalid(
                    "sha256 manifest is missing file checksum",
                    errors=[{"file": file_name}],
                )
            actual = hashlib.sha256(raw).hexdigest()
            if actual != expected:
                raise ProfileImportError(
                    detail="Archive checksum mismatch",
                    code="PROFILE_IMPORT_CORRUPT",
                    errors=[{"file": file_name}],
                    status_code=400,
                )

    return manifest, data_bytes


def _load_rows(
    raw: bytes,
    model: type[_ImportModel],
    file_name: str,
) -> list[_ImportModel]:
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        _raise_invalid(
            f"Invalid JSON in {file_name}",
            errors=[{"file": file_name, "msg": str(exc)}],
        )

    if not isinstance(data, list):
        _raise_invalid(
            f"{file_name} must contain a JSON array",
            errors=[{"file": file_name}],
        )

    parsed: list[_ImportModel] = []
    errors: list[dict[str, Any]] = []
    for index, row in enumerate(data):
        try:
            parsed.append(model.model_validate(row))
        except ValidationError as exc:
            errors.append({"file": file_name, "index": index, "msg": str(exc)})

    if errors:
        _raise_invalid(f"Validation failed for {file_name}", errors=errors)
    return parsed


def _load_rows_if_present(
    data_bytes: dict[str, bytes],
    file_name: str,
    model: type[_ImportModel],
) -> list[_ImportModel]:
    raw = data_bytes.get(file_name)
    if raw is None:
        return []
    return _load_rows(raw, model, file_name)


def _check_fk(
    mapping: dict[int, int],
    legacy_id: int,
    file_name: str,
    field: str,
) -> int:
    resolved = mapping.get(legacy_id)
    if resolved is None:
        _raise_invalid(
            f"Unresolved foreign key in {file_name}",
            errors=[{"file": file_name, "field": field, "legacy_id": legacy_id}],
        )
    return resolved


def _delete_user_domain_data(session: Session, user_id: uuid.UUID) -> None:
    session.execute(
        delete(AlgorithmTrainingAttempt).where(
            AlgorithmTrainingAttempt.user_id == user_id
        )
    )
    session.execute(
        delete(AlgorithmReviewAttempt).where(AlgorithmReviewAttempt.user_id == user_id)
    )
    session.execute(
        delete(AlgorithmReviewItem).where(AlgorithmReviewItem.user_id == user_id)
    )
    session.execute(
        delete(AlgorithmCodeSnippet).where(AlgorithmCodeSnippet.user_id == user_id)
    )
    session.execute(delete(Algorithm).where(Algorithm.user_id == user_id))
    session.execute(delete(AlgorithmGroup).where(AlgorithmGroup.user_id == user_id))

    session.execute(delete(ReviewAttempt).where(ReviewAttempt.user_id == user_id))
    session.execute(
        delete(ReviewScheduleItem).where(ReviewScheduleItem.user_id == user_id)
    )
    session.execute(delete(ReadingPart).where(ReadingPart.user_id == user_id))
    session.execute(delete(Book).where(Book.user_id == user_id))
    session.execute(delete(UserSettings).where(UserSettings.user_id == user_id))


def _warn_existing_titles(
    session: Session,
    user: User,
    books: list[BookIn],
    groups: list[AlgorithmGroupIn],
) -> list[str]:
    warnings: list[str] = []

    existing_book_titles = {
        title.strip().lower()
        for title in session.execute(
            select(Book.title).where(Book.user_id == user.id)
        ).scalars()
    }
    matched_books = sorted(
        {
            item.title.strip()
            for item in books
            if item.title.strip().lower() in existing_book_titles
        }
    )
    if matched_books:
        if len(matched_books) > MERGE_WARNING_THRESHOLD:
            warnings.append(
                "Found "
                f"{len(matched_books)} imported books matching existing titles."
            )
        else:
            warnings.append(
                "Imported books matching existing titles: " + ", ".join(matched_books)
            )

    existing_group_norms = {
        title_norm
        for title_norm in session.execute(
            select(AlgorithmGroup.title_norm).where(AlgorithmGroup.user_id == user.id)
        ).scalars()
    }
    matched_groups = sorted(
        {
            item.title.strip()
            for item in groups
            if normalize_group_title(item.title) in existing_group_norms
        }
    )
    if matched_groups:
        if len(matched_groups) > MERGE_WARNING_THRESHOLD:
            warnings.append(
                "Found "
                f"{len(matched_groups)} imported algorithm groups matching "
                "existing title_norm."
            )
        else:
            warnings.append(
                "Imported algorithm groups matching existing title_norm: "
                + ", ".join(matched_groups)
            )

    return warnings


def _resolve_group_title(
    session: Session,
    user_id: uuid.UUID,
    desired_title: str,
    legacy_id: int,
) -> tuple[str, str | None]:
    normalized = normalize_group_title(desired_title)
    exists = session.execute(
        select(func.count(AlgorithmGroup.id)).where(
            AlgorithmGroup.user_id == user_id,
            AlgorithmGroup.title_norm == normalized,
        )
    ).scalar_one()
    if not exists:
        return desired_title, None

    base = desired_title.strip() or "Imported Group"
    candidate = f"{base} (import {legacy_id})"
    suffix = 2
    while True:
        candidate_norm = normalize_group_title(candidate)
        conflict = session.execute(
            select(func.count(AlgorithmGroup.id)).where(
                AlgorithmGroup.user_id == user_id,
                AlgorithmGroup.title_norm == candidate_norm,
            )
        ).scalar_one()
        if not conflict:
            return (
                candidate,
                "Adjusted algorithm group title "
                f"'{desired_title}' to '{candidate}' due to uniqueness "
                "constraint.",
            )
        candidate = f"{base} (import {legacy_id}-{suffix})"
        suffix += 1


def import_profile_zip(
    session: Session,
    user: User,
    file_bytes: bytes,
    *,
    mode: ImportMode = "merge",
    confirm_replace: bool = False,
) -> dict[str, Any]:
    """Import profile ZIP for the current user."""
    if mode == "replace" and not confirm_replace:
        raise ProfileImportError(
            detail="replace mode requires confirm_replace=true",
            code="PROFILE_IMPORT_CONFIRM_REQUIRED",
            status_code=400,
        )

    _manifest, data_bytes = _load_zip(file_bytes)

    books = _load_rows_if_present(data_bytes, "data/books.json", BookIn)
    parts = _load_rows_if_present(data_bytes, "data/reading_parts.json", ReadingPartIn)
    review_items = _load_rows_if_present(
        data_bytes,
        "data/review_schedule_items.json",
        ReviewItemIn,
    )
    review_attempts = _load_rows_if_present(
        data_bytes,
        "data/review_attempts.json",
        ReviewAttemptIn,
    )
    groups = _load_rows_if_present(
        data_bytes,
        "data/algorithm_groups.json",
        AlgorithmGroupIn,
    )
    algorithms = _load_rows_if_present(data_bytes, "data/algorithms.json", AlgorithmIn)
    snippets = _load_rows_if_present(
        data_bytes,
        "data/algorithm_code_snippets.json",
        AlgorithmCodeSnippetIn,
    )
    algorithm_review_items = _load_rows_if_present(
        data_bytes,
        "data/algorithm_review_items.json",
        AlgorithmReviewItemIn,
    )
    algorithm_review_attempts = _load_rows_if_present(
        data_bytes,
        "data/algorithm_review_attempts.json",
        AlgorithmReviewAttemptIn,
    )
    algorithm_training_attempts = _load_rows_if_present(
        data_bytes,
        "data/algorithm_training_attempts.json",
        AlgorithmTrainingAttemptIn,
    )

    settings_rows = _load_rows_if_present(
        data_bytes,
        "data/user_settings.json",
        UserSettingsIn,
    )
    if len(settings_rows) > 1:
        _raise_invalid(
            "data/user_settings.json must contain at most one record",
            errors=[{"file": "data/user_settings.json"}],
        )

    warnings: list[str] = []
    if mode == "merge":
        warnings.extend(_warn_existing_titles(session, user, books, groups))

    imported: dict[str, int] = {
        "books": 0,
        "reading_parts": 0,
        "review_schedule_items": 0,
        "review_attempts": 0,
        "algorithm_groups": 0,
        "algorithms": 0,
        "algorithm_code_snippets": 0,
        "algorithm_review_items": 0,
        "algorithm_review_attempts": 0,
        "algorithm_training_attempts": 0,
        "user_settings": 0,
    }
    skipped: dict[str, int] = {"user_settings": 0}

    book_map: dict[int, int] = {}
    part_map: dict[int, int] = {}
    review_item_map: dict[int, int] = {}
    group_map: dict[int, int] = {}
    algorithm_map: dict[int, int] = {}
    algorithm_review_item_map: dict[int, int] = {}

    title_adjustment_messages: list[str] = []
    title_adjustments_count = 0

    try:
        if mode == "replace":
            _delete_user_domain_data(session, user.id)

        for row in books:
            entity = Book(
                user_id=user.id,
                title=row.title,
                author=row.author,
                status=row.status,
                pages_total=row.pages_total,
            )
            session.add(entity)
            session.flush()
            book_map[row.legacy_id] = entity.id
            imported["books"] += 1

        for row in parts:
            entity = ReadingPart(
                user_id=user.id,
                book_id=_check_fk(
                    book_map,
                    row.book_legacy_id,
                    "data/reading_parts.json",
                    "book_legacy_id",
                ),
                part_index=row.part_index,
                label=row.label,
                created_at=row.created_at,
                raw_notes=row.raw_notes,
                gpt_summary=row.gpt_summary,
                gpt_questions_by_interval=row.gpt_questions_by_interval,
                pages_read=row.pages_read,
                session_seconds=row.session_seconds,
                page_end=row.page_end,
            )
            session.add(entity)
            session.flush()
            part_map[row.legacy_id] = entity.id
            imported["reading_parts"] += 1

        for row in review_items:
            entity = ReviewScheduleItem(
                user_id=user.id,
                reading_part_id=_check_fk(
                    part_map,
                    row.reading_part_legacy_id,
                    "data/review_schedule_items.json",
                    "reading_part_legacy_id",
                ),
                interval_days=row.interval_days,
                due_date=row.due_date,
                status=row.status,
                completed_at=row.completed_at,
                questions=row.questions,
            )
            session.add(entity)
            session.flush()
            review_item_map[row.legacy_id] = entity.id
            imported["review_schedule_items"] += 1

        for row in review_attempts:
            entity = ReviewAttempt(
                user_id=user.id,
                review_item_id=_check_fk(
                    review_item_map,
                    row.review_item_legacy_id,
                    "data/review_attempts.json",
                    "review_item_legacy_id",
                ),
                answers=row.answers,
                created_at=row.created_at,
                gpt_check_result=row.gpt_check_result,
                gpt_check_payload=row.gpt_check_payload,
                gpt_rating_1_to_5=row.gpt_rating_1_to_5,
                gpt_score_0_to_100=row.gpt_score_0_to_100,
                gpt_verdict=row.gpt_verdict,
            )
            session.add(entity)
            session.flush()
            imported["review_attempts"] += 1

        for row in groups:
            title = row.title
            if mode == "merge":
                title, adjustment_message = _resolve_group_title(
                    session,
                    user.id,
                    row.title,
                    row.legacy_id,
                )
                if adjustment_message:
                    title_adjustments_count += 1
                    if len(title_adjustment_messages) < MERGE_WARNING_THRESHOLD:
                        title_adjustment_messages.append(adjustment_message)

            entity = AlgorithmGroup(
                user_id=user.id,
                title=title,
                description=row.description,
                notes=row.notes,
                created_at=row.created_at,
                updated_at=row.updated_at,
            )
            session.add(entity)
            session.flush()
            group_map[row.legacy_id] = entity.id
            imported["algorithm_groups"] += 1

        for row in algorithms:
            source_part_id = None
            if row.source_part_legacy_id is not None:
                source_part_id = _check_fk(
                    part_map,
                    row.source_part_legacy_id,
                    "data/algorithms.json",
                    "source_part_legacy_id",
                )

            entity = Algorithm(
                user_id=user.id,
                group_id=_check_fk(
                    group_map,
                    row.group_legacy_id,
                    "data/algorithms.json",
                    "group_legacy_id",
                ),
                source_part_id=source_part_id,
                title=row.title,
                summary=row.summary,
                when_to_use=row.when_to_use,
                complexity=row.complexity,
                invariants=row.invariants,
                steps=row.steps,
                corner_cases=row.corner_cases,
                created_at=row.created_at,
                updated_at=row.updated_at,
            )
            session.add(entity)
            session.flush()
            algorithm_map[row.legacy_id] = entity.id
            imported["algorithms"] += 1

        for row in snippets:
            entity = AlgorithmCodeSnippet(
                user_id=user.id,
                algorithm_id=_check_fk(
                    algorithm_map,
                    row.algorithm_legacy_id,
                    "data/algorithm_code_snippets.json",
                    "algorithm_legacy_id",
                ),
                code_kind=row.code_kind,
                language=row.language,
                code_text=row.code_text,
                is_reference=row.is_reference,
                created_at=row.created_at,
            )
            session.add(entity)
            session.flush()
            imported["algorithm_code_snippets"] += 1

        for row in algorithm_review_items:
            entity = AlgorithmReviewItem(
                user_id=user.id,
                algorithm_id=_check_fk(
                    algorithm_map,
                    row.algorithm_legacy_id,
                    "data/algorithm_review_items.json",
                    "algorithm_legacy_id",
                ),
                interval_days=row.interval_days,
                due_date=row.due_date,
                status=row.status,
                completed_at=row.completed_at,
                questions=row.questions,
            )
            session.add(entity)
            session.flush()
            algorithm_review_item_map[row.legacy_id] = entity.id
            imported["algorithm_review_items"] += 1

        for row in algorithm_review_attempts:
            entity = AlgorithmReviewAttempt(
                user_id=user.id,
                review_item_id=_check_fk(
                    algorithm_review_item_map,
                    row.review_item_legacy_id,
                    "data/algorithm_review_attempts.json",
                    "review_item_legacy_id",
                ),
                answers=row.answers,
                gpt_check_json=row.gpt_check_json,
                rating_1_to_5=row.rating_1_to_5,
                created_at=row.created_at,
            )
            session.add(entity)
            session.flush()
            imported["algorithm_review_attempts"] += 1

        for row in algorithm_training_attempts:
            entity = AlgorithmTrainingAttempt(
                user_id=user.id,
                algorithm_id=_check_fk(
                    algorithm_map,
                    row.algorithm_legacy_id,
                    "data/algorithm_training_attempts.json",
                    "algorithm_legacy_id",
                ),
                mode=row.mode,
                code_text=row.code_text,
                gpt_check_json=row.gpt_check_json,
                rating_1_to_5=row.rating_1_to_5,
                accuracy=row.accuracy,
                duration_sec=row.duration_sec,
                created_at=row.created_at,
            )
            session.add(entity)
            session.flush()
            imported["algorithm_training_attempts"] += 1

        if settings_rows:
            settings_row = settings_rows[0]
            existing_settings = session.get(UserSettings, user.id)
            if existing_settings:
                for field in [
                    "timezone",
                    "pomodoro_work_min",
                    "pomodoro_break_min",
                    "daily_goal_weekday_min",
                    "daily_goal_weekend_min",
                    "intervals_days",
                ]:
                    setattr(existing_settings, field, getattr(settings_row, field))
            else:
                session.add(
                    UserSettings(
                        user_id=user.id,
                        timezone=settings_row.timezone,
                        pomodoro_work_min=settings_row.pomodoro_work_min,
                        pomodoro_break_min=settings_row.pomodoro_break_min,
                        daily_goal_weekday_min=settings_row.daily_goal_weekday_min,
                        daily_goal_weekend_min=settings_row.daily_goal_weekend_min,
                        intervals_days=settings_row.intervals_days,
                    )
                )
            imported["user_settings"] = 1
        else:
            skipped["user_settings"] = 1

        session.commit()
    except ProfileImportError:
        session.rollback()
        raise
    except Exception as exc:
        session.rollback()
        raise ProfileImportError(
            detail="Failed to import profile",
            code="PROFILE_IMPORT_INVALID",
            errors=[{"msg": str(exc)}],
            status_code=400,
        ) from exc

    if title_adjustments_count:
        if title_adjustments_count > MERGE_WARNING_THRESHOLD:
            warnings.append(
                "Adjusted "
                f"{title_adjustments_count} algorithm group titles due to "
                "uniqueness constraint."
            )
        else:
            warnings.extend(title_adjustment_messages)

    return {
        "status": "ok",
        "imported": imported,
        "skipped": skipped,
        "warnings": warnings,
    }
