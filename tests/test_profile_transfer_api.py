"""Profile export/import API integration tests."""

from __future__ import annotations

import hashlib
import io
import json
import uuid
from datetime import date, datetime, timezone
from zipfile import ZIP_DEFLATED, ZipFile

from fastapi.testclient import TestClient
from sqlalchemy import func, select
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
from studying_light.services import profile_import as profile_import_service


def _get_user(session: Session, email: str) -> User:
    return session.execute(select(User).where(User.email == email)).scalar_one()


def _seed_full_profile(session: Session, user: User, marker: str) -> None:
    now = datetime.now(timezone.utc)

    book = Book(
        user_id=user.id,
        title=f"{marker} Book",
        author="Author",
        status="active",
        pages_total=300,
    )
    session.add(book)
    session.flush()

    part = ReadingPart(
        user_id=user.id,
        book_id=book.id,
        part_index=1,
        label=f"{marker} Part",
        created_at=now,
        raw_notes={"text": "notes"},
        gpt_summary="summary",
        gpt_questions_by_interval={"1": ["q"]},
        pages_read=25,
        session_seconds=1200,
        page_end=25,
    )
    session.add(part)
    session.flush()

    review_item = ReviewScheduleItem(
        user_id=user.id,
        reading_part_id=part.id,
        interval_days=1,
        due_date=date.today(),
        status="planned",
        questions=["what?"],
    )
    session.add(review_item)
    session.flush()

    review_attempt = ReviewAttempt(
        user_id=user.id,
        review_item_id=review_item.id,
        answers={"q": "a"},
        created_at=now,
        gpt_check_result="ok",
        gpt_check_payload={"score": 80},
        gpt_rating_1_to_5=4,
        gpt_score_0_to_100=80,
        gpt_verdict="good",
    )
    session.add(review_attempt)

    group = AlgorithmGroup(
        user_id=user.id,
        title=f"{marker} Group",
        description="desc",
        notes="notes",
        created_at=now,
        updated_at=now,
    )
    session.add(group)
    session.flush()

    algorithm = Algorithm(
        user_id=user.id,
        group_id=group.id,
        source_part_id=part.id,
        title=f"{marker} Algorithm",
        summary="summary",
        when_to_use="when",
        complexity="O(n)",
        invariants=["inv"],
        steps=["step"],
        corner_cases=["edge"],
        created_at=now,
        updated_at=now,
    )
    session.add(algorithm)
    session.flush()

    snippet = AlgorithmCodeSnippet(
        user_id=user.id,
        algorithm_id=algorithm.id,
        code_kind="pseudocode",
        language="text",
        code_text="code",
        is_reference=True,
        created_at=now,
    )
    session.add(snippet)

    algorithm_review_item = AlgorithmReviewItem(
        user_id=user.id,
        algorithm_id=algorithm.id,
        interval_days=1,
        due_date=date.today(),
        status="planned",
        questions=["q1"],
    )
    session.add(algorithm_review_item)
    session.flush()

    algorithm_review_attempt = AlgorithmReviewAttempt(
        user_id=user.id,
        review_item_id=algorithm_review_item.id,
        answers={"q": "a"},
        gpt_check_json={"ok": True},
        rating_1_to_5=5,
        created_at=now,
    )
    session.add(algorithm_review_attempt)

    training_attempt = AlgorithmTrainingAttempt(
        user_id=user.id,
        algorithm_id=algorithm.id,
        mode="memory",
        code_text="attempt",
        gpt_check_json={"ok": True},
        rating_1_to_5=4,
        accuracy=92.0,
        duration_sec=42,
        created_at=now,
    )
    session.add(training_attempt)

    settings = session.get(UserSettings, user.id)
    if settings:
        settings.timezone = "UTC"
        settings.pomodoro_work_min = 25
        settings.pomodoro_break_min = 5
        settings.daily_goal_weekday_min = 30
        settings.daily_goal_weekend_min = 45
        settings.intervals_days = [1, 7, 16, 35, 90]
    else:
        settings = UserSettings(
            user_id=user.id,
            timezone="UTC",
            pomodoro_work_min=25,
            pomodoro_break_min=5,
            daily_goal_weekday_min=30,
            daily_goal_weekend_min=45,
            intervals_days=[1, 7, 16, 35, 90],
        )
        session.add(settings)
    session.commit()


def _counts(session: Session, user_id: uuid.UUID) -> dict[str, int]:
    return {
        "books": session.execute(
            select(func.count(Book.id)).where(Book.user_id == user_id)
        ).scalar_one(),
        "reading_parts": session.execute(
            select(func.count(ReadingPart.id)).where(ReadingPart.user_id == user_id)
        ).scalar_one(),
        "review_schedule_items": session.execute(
            select(func.count(ReviewScheduleItem.id)).where(
                ReviewScheduleItem.user_id == user_id
            )
        ).scalar_one(),
        "review_attempts": session.execute(
            select(func.count(ReviewAttempt.id)).where(ReviewAttempt.user_id == user_id)
        ).scalar_one(),
        "algorithm_groups": session.execute(
            select(func.count(AlgorithmGroup.id)).where(
                AlgorithmGroup.user_id == user_id
            )
        ).scalar_one(),
        "algorithms": session.execute(
            select(func.count(Algorithm.id)).where(Algorithm.user_id == user_id)
        ).scalar_one(),
        "algorithm_code_snippets": session.execute(
            select(func.count(AlgorithmCodeSnippet.id)).where(
                AlgorithmCodeSnippet.user_id == user_id
            )
        ).scalar_one(),
        "algorithm_review_items": session.execute(
            select(func.count(AlgorithmReviewItem.id)).where(
                AlgorithmReviewItem.user_id == user_id
            )
        ).scalar_one(),
        "algorithm_review_attempts": session.execute(
            select(func.count(AlgorithmReviewAttempt.id)).where(
                AlgorithmReviewAttempt.user_id == user_id
            )
        ).scalar_one(),
        "algorithm_training_attempts": session.execute(
            select(func.count(AlgorithmTrainingAttempt.id)).where(
                AlgorithmTrainingAttempt.user_id == user_id
            )
        ).scalar_one(),
        "user_settings": session.execute(
            select(func.count(UserSettings.user_id)).where(
                UserSettings.user_id == user_id
            )
        ).scalar_one(),
    }


def _read_zip_entries(payload: bytes) -> dict[str, bytes]:
    with ZipFile(io.BytesIO(payload)) as archive:
        return {name: archive.read(name) for name in archive.namelist()}


def _write_zip_entries(entries: dict[str, bytes]) -> bytes:
    buffer = io.BytesIO()
    with ZipFile(buffer, "w", ZIP_DEFLATED) as archive:
        for name, raw in entries.items():
            archive.writestr(name, raw)
    return buffer.getvalue()


def test_profile_export_zip_contains_manifest_and_sha256(
    client: TestClient,
    session: Session,
    auth_headers: dict[str, str],
) -> None:
    user = _get_user(session, "user@local")
    _seed_full_profile(session, user, "SRC")

    response = client.get("/api/v1/profile-export.zip", headers=auth_headers)
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/zip")

    entries = _read_zip_entries(response.content)
    assert "manifest.json" in entries

    required = {
        "data/books.json",
        "data/reading_parts.json",
        "data/review_schedule_items.json",
        "data/review_attempts.json",
        "data/algorithm_groups.json",
        "data/algorithms.json",
        "data/algorithm_code_snippets.json",
        "data/algorithm_review_items.json",
        "data/algorithm_review_attempts.json",
        "data/algorithm_training_attempts.json",
        "data/user_settings.json",
    }
    assert required.issubset(entries.keys())

    manifest = json.loads(entries["manifest.json"])
    assert manifest["format"] == "studying-light-profile"
    assert manifest["format_version"] == 1

    for file_name, digest in manifest["sha256"].items():
        assert hashlib.sha256(entries[file_name]).hexdigest() == digest


def test_profile_import_merge_roundtrip_preserves_counts(
    client: TestClient,
    session: Session,
    user_pair_headers: tuple[dict[str, str], dict[str, str]],
) -> None:
    source_headers, target_headers = user_pair_headers
    source_user = _get_user(session, "user-a@local")
    target_user = _get_user(session, "user-b@local")

    _seed_full_profile(session, source_user, "SRC")
    expected = _counts(session, source_user.id)

    export_response = client.get("/api/v1/profile-export.zip", headers=source_headers)
    assert export_response.status_code == 200

    import_response = client.post(
        "/api/v1/profile-import?mode=merge",
        files={"file": ("profile.zip", export_response.content, "application/zip")},
        headers=target_headers,
    )
    assert import_response.status_code == 200
    payload = import_response.json()
    assert payload["status"] == "ok"
    assert payload["imported"]["books"] == expected["books"]

    actual = _counts(session, target_user.id)
    assert actual == expected


def test_profile_import_replace_overwrites_existing_data(
    client: TestClient,
    session: Session,
    user_pair_headers: tuple[dict[str, str], dict[str, str]],
) -> None:
    source_headers, target_headers = user_pair_headers
    source_user = _get_user(session, "user-a@local")
    target_user = _get_user(session, "user-b@local")

    _seed_full_profile(session, source_user, "SRC")
    _seed_full_profile(session, target_user, "OLD")

    export_response = client.get("/api/v1/profile-export.zip", headers=source_headers)
    assert export_response.status_code == 200

    replace_response = client.post(
        "/api/v1/profile-import?mode=replace&confirm_replace=true",
        files={"file": ("profile.zip", export_response.content, "application/zip")},
        headers=target_headers,
    )
    assert replace_response.status_code == 200

    expected = _counts(session, source_user.id)
    actual = _counts(session, target_user.id)
    assert actual == expected


def test_profile_import_negative_manifest_and_integrity_errors(
    client: TestClient,
    session: Session,
    auth_headers: dict[str, str],
) -> None:
    user = _get_user(session, "user@local")
    _seed_full_profile(session, user, "SRC")

    export_response = client.get("/api/v1/profile-export.zip", headers=auth_headers)
    assert export_response.status_code == 200
    base_entries = _read_zip_entries(export_response.content)

    wrong_version_entries = dict(base_entries)
    wrong_manifest = json.loads(wrong_version_entries["manifest.json"])
    wrong_manifest["format_version"] = 999
    wrong_version_entries["manifest.json"] = json.dumps(wrong_manifest).encode("utf-8")
    wrong_version_response = client.post(
        "/api/v1/profile-import",
        files={
            "file": (
                "wrong-version.zip",
                _write_zip_entries(wrong_version_entries),
                "application/zip",
            )
        },
        headers=auth_headers,
    )
    assert wrong_version_response.status_code == 422
    assert wrong_version_response.json()["code"] == "PROFILE_IMPORT_UNSUPPORTED_VERSION"

    bad_sha_entries = dict(base_entries)
    bad_sha_manifest = json.loads(bad_sha_entries["manifest.json"])
    bad_sha_manifest["sha256"]["data/books.json"] = "deadbeef"
    bad_sha_entries["manifest.json"] = json.dumps(bad_sha_manifest).encode("utf-8")
    bad_sha_response = client.post(
        "/api/v1/profile-import",
        files={
            "file": (
                "bad-sha.zip",
                _write_zip_entries(bad_sha_entries),
                "application/zip",
            )
        },
        headers=auth_headers,
    )
    assert bad_sha_response.status_code == 400
    assert bad_sha_response.json()["code"] == "PROFILE_IMPORT_CORRUPT"

    missing_file_entries = dict(base_entries)
    missing_file_entries.pop("data/books.json")
    missing_file_response = client.post(
        "/api/v1/profile-import",
        files={
            "file": (
                "missing-file.zip",
                _write_zip_entries(missing_file_entries),
                "application/zip",
            )
        },
        headers=auth_headers,
    )
    assert missing_file_response.status_code == 400
    assert missing_file_response.json()["code"] == "PROFILE_IMPORT_INVALID"


def test_profile_import_ignores_foreign_user_id_from_archive(
    client: TestClient,
    session: Session,
    user_pair_headers: tuple[dict[str, str], dict[str, str]],
) -> None:
    source_headers, target_headers = user_pair_headers
    source_user = _get_user(session, "user-a@local")
    target_user = _get_user(session, "user-b@local")

    _seed_full_profile(session, source_user, "SRC")

    export_response = client.get("/api/v1/profile-export.zip", headers=source_headers)
    assert export_response.status_code == 200

    entries = _read_zip_entries(export_response.content)
    books = json.loads(entries["data/books.json"])
    foreign_user_id = str(uuid.uuid4())
    for row in books:
        row["user_id"] = foreign_user_id
    entries["data/books.json"] = json.dumps(books).encode("utf-8")

    manifest = json.loads(entries["manifest.json"])
    manifest["sha256"]["data/books.json"] = hashlib.sha256(
        entries["data/books.json"]
    ).hexdigest()
    entries["manifest.json"] = json.dumps(manifest).encode("utf-8")

    import_response = client.post(
        "/api/v1/profile-import",
        files={
            "file": (
                "tampered-user-id.zip",
                _write_zip_entries(entries),
                "application/zip",
            )
        },
        headers=target_headers,
    )
    assert import_response.status_code == 200

    imported_books = (
        session.execute(select(Book).where(Book.user_id == target_user.id))
        .scalars()
        .all()
    )
    assert imported_books
    assert all(str(book.user_id) != foreign_user_id for book in imported_books)


def test_profile_import_rejects_zip_slip_archive(
    client: TestClient,
    session: Session,
    auth_headers: dict[str, str],
) -> None:
    user = _get_user(session, "user@local")
    _seed_full_profile(session, user, "SRC")

    export_response = client.get("/api/v1/profile-export.zip", headers=auth_headers)
    assert export_response.status_code == 200

    entries = _read_zip_entries(export_response.content)
    entries["../evil.txt"] = b"boom"
    attack_archive = _write_zip_entries(entries)

    response = client.post(
        "/api/v1/profile-import",
        files={"file": ("zip-slip.zip", attack_archive, "application/zip")},
        headers=auth_headers,
    )
    assert response.status_code == 400
    assert response.json()["code"] == "PROFILE_IMPORT_CORRUPT"


def test_profile_import_rejects_archive_extracted_size_over_limit(
    client: TestClient,
    session: Session,
    auth_headers: dict[str, str],
    monkeypatch,
) -> None:
    user = _get_user(session, "user@local")
    _seed_full_profile(session, user, "SRC")
    monkeypatch.setattr(profile_import_service, "MAX_TOTAL_EXTRACTED_SIZE_BYTES", 32)

    export_response = client.get("/api/v1/profile-export.zip", headers=auth_headers)
    assert export_response.status_code == 200

    response = client.post(
        "/api/v1/profile-import",
        files={
            "file": (
                "too-large-unpacked.zip",
                export_response.content,
                "application/zip",
            )
        },
        headers=auth_headers,
    )
    assert response.status_code == 413
    assert response.json()["code"] == "PROFILE_IMPORT_TOO_LARGE"


def test_profile_import_replace_rolls_back_on_import_error(
    client: TestClient,
    session: Session,
    user_pair_headers: tuple[dict[str, str], dict[str, str]],
) -> None:
    source_headers, target_headers = user_pair_headers
    source_user = _get_user(session, "user-a@local")
    target_user = _get_user(session, "user-b@local")

    _seed_full_profile(session, source_user, "SRC")
    _seed_full_profile(session, target_user, "KEEP")
    before = _counts(session, target_user.id)

    export_response = client.get("/api/v1/profile-export.zip", headers=source_headers)
    assert export_response.status_code == 200

    entries = _read_zip_entries(export_response.content)
    parts = json.loads(entries["data/reading_parts.json"])
    parts[0]["book_legacy_id"] = 999999
    entries["data/reading_parts.json"] = json.dumps(parts).encode("utf-8")

    manifest = json.loads(entries["manifest.json"])
    manifest["sha256"]["data/reading_parts.json"] = hashlib.sha256(
        entries["data/reading_parts.json"]
    ).hexdigest()
    entries["manifest.json"] = json.dumps(manifest).encode("utf-8")

    response = client.post(
        "/api/v1/profile-import?mode=replace&confirm_replace=true",
        files={
            "file": (
                "replace-rollback.zip",
                _write_zip_entries(entries),
                "application/zip",
            )
        },
        headers=target_headers,
    )
    assert response.status_code == 400
    assert response.json()["code"] == "PROFILE_IMPORT_INVALID"

    after = _counts(session, target_user.id)
    assert after == before


def test_profile_import_compat_missing_file_when_manifest_indicates_empty(
    client: TestClient,
    session: Session,
    auth_headers: dict[str, str],
) -> None:
    user = _get_user(session, "user@local")
    _seed_full_profile(session, user, "SRC")

    export_response = client.get("/api/v1/profile-export.zip", headers=auth_headers)
    assert export_response.status_code == 200

    entries = _read_zip_entries(export_response.content)
    entries.pop("data/algorithm_training_attempts.json")
    manifest = json.loads(entries["manifest.json"])
    manifest["counts"].pop("algorithm_training_attempts", None)
    manifest["sha256"].pop("data/algorithm_training_attempts.json")
    manifest["data_files"] = [
        file_name
        for file_name in manifest["data_files"]
        if file_name != "data/algorithm_training_attempts.json"
    ]
    entries["manifest.json"] = json.dumps(manifest).encode("utf-8")

    response = client.post(
        "/api/v1/profile-import?mode=merge",
        files={
            "file": (
                "compat-missing-training.zip",
                _write_zip_entries(entries),
                "application/zip",
            )
        },
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
