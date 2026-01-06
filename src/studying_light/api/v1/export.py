"""Export endpoints."""

import csv
import io
import json
from datetime import date, datetime
from zipfile import ZIP_DEFLATED, ZipFile

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from studying_light.db.models.book import Book
from studying_light.db.models.reading_part import ReadingPart
from studying_light.db.models.review_schedule_item import ReviewScheduleItem
from studying_light.db.session import get_session

router: APIRouter = APIRouter()

EXPORT_COLUMNS: list[str] = [
    "entity",
    "id",
    "book_id",
    "reading_part_id",
    "part_index",
    "title",
    "author",
    "status",
    "pages_total",
    "label",
    "created_at",
    "raw_notes",
    "gpt_summary",
    "gpt_questions_by_interval",
    "pages_read",
    "session_seconds",
    "interval_days",
    "due_date",
    "completed_at",
    "questions",
]


def _serialize(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return str(value)


def _build_csv(rows: list[dict[str, object]]) -> str:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=EXPORT_COLUMNS)
    writer.writeheader()
    for row in rows:
        prepared = {key: _serialize(row.get(key)) for key in EXPORT_COLUMNS}
        writer.writerow(prepared)
    return buffer.getvalue()


def _collect_rows(session: Session) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    books = session.execute(select(Book).order_by(Book.id)).scalars().all()
    for book in books:
        rows.append(
            {
                "entity": "book",
                "id": book.id,
                "title": book.title,
                "author": book.author,
                "status": book.status,
                "pages_total": book.pages_total,
            }
        )

    parts = (
        session.execute(select(ReadingPart).order_by(ReadingPart.id))
        .scalars()
        .all()
    )
    for part in parts:
        rows.append(
            {
                "entity": "part",
                "id": part.id,
                "book_id": part.book_id,
                "part_index": part.part_index,
                "label": part.label,
                "created_at": part.created_at,
                "raw_notes": part.raw_notes,
                "gpt_summary": part.gpt_summary,
                "gpt_questions_by_interval": part.gpt_questions_by_interval,
                "pages_read": part.pages_read,
                "session_seconds": part.session_seconds,
            }
        )

    reviews = (
        session.execute(select(ReviewScheduleItem).order_by(ReviewScheduleItem.id))
        .scalars()
        .all()
    )
    for review in reviews:
        rows.append(
            {
                "entity": "review",
                "id": review.id,
                "reading_part_id": review.reading_part_id,
                "interval_days": review.interval_days,
                "due_date": review.due_date,
                "status": review.status,
                "completed_at": review.completed_at,
                "questions": review.questions,
            }
        )
    return rows


def _build_table_csv(rows: list[dict[str, object]], columns: list[str]) -> str:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=columns)
    writer.writeheader()
    for row in rows:
        prepared = {key: _serialize(row.get(key)) for key in columns}
        writer.writerow(prepared)
    return buffer.getvalue()


@router.get("/export.csv")
def export_csv(session: Session = Depends(get_session)) -> StreamingResponse:
    """Export data as a single CSV."""
    rows = _collect_rows(session)
    csv_text = _build_csv(rows)
    data = csv_text.encode("utf-8")
    headers = {"Content-Disposition": "attachment; filename=export.csv"}
    return StreamingResponse(
        io.BytesIO(data),
        media_type="text/csv; charset=utf-8",
        headers=headers,
    )


@router.get("/export.zip")
def export_zip(session: Session = Depends(get_session)) -> StreamingResponse:
    """Export data as a ZIP archive with CSV files."""
    books = session.execute(select(Book).order_by(Book.id)).scalars().all()
    parts = (
        session.execute(select(ReadingPart).order_by(ReadingPart.id))
        .scalars()
        .all()
    )
    reviews = (
        session.execute(select(ReviewScheduleItem).order_by(ReviewScheduleItem.id))
        .scalars()
        .all()
    )

    book_rows = [
        {
            "id": book.id,
            "title": book.title,
            "author": book.author,
            "status": book.status,
            "pages_total": book.pages_total,
        }
        for book in books
    ]
    part_rows = [
        {
            "id": part.id,
            "book_id": part.book_id,
            "part_index": part.part_index,
            "label": part.label,
            "created_at": part.created_at,
            "raw_notes": part.raw_notes,
            "gpt_summary": part.gpt_summary,
            "gpt_questions_by_interval": part.gpt_questions_by_interval,
            "pages_read": part.pages_read,
            "session_seconds": part.session_seconds,
        }
        for part in parts
    ]
    review_rows = [
        {
            "id": review.id,
            "reading_part_id": review.reading_part_id,
            "interval_days": review.interval_days,
            "due_date": review.due_date,
            "status": review.status,
            "completed_at": review.completed_at,
            "questions": review.questions,
        }
        for review in reviews
    ]

    book_csv = _build_table_csv(
        book_rows, ["id", "title", "author", "status", "pages_total"]
    )
    part_csv = _build_table_csv(
        part_rows,
        [
            "id",
            "book_id",
            "part_index",
            "label",
            "created_at",
            "raw_notes",
            "gpt_summary",
            "gpt_questions_by_interval",
            "pages_read",
            "session_seconds",
        ],
    )
    review_csv = _build_table_csv(
        review_rows,
        [
            "id",
            "reading_part_id",
            "interval_days",
            "due_date",
            "status",
            "completed_at",
            "questions",
        ],
    )

    buffer = io.BytesIO()
    with ZipFile(buffer, "w", ZIP_DEFLATED) as archive:
        archive.writestr("books.csv", book_csv)
        archive.writestr("parts.csv", part_csv)
        archive.writestr("reviews.csv", review_csv)
    buffer.seek(0)
    headers = {"Content-Disposition": "attachment; filename=export.zip"}
    return StreamingResponse(
        buffer,
        media_type="application/zip",
        headers=headers,
    )
