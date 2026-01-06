"""Reading part endpoints."""

from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from studying_light.api.v1.schemas import ImportGptPayload, ImportGptResponse
from studying_light.api.v1.schemas import ReadingPartCreate, ReadingPartOut, ReviewItemOut
from studying_light.db.models.book import Book
from studying_light.db.models.reading_part import ReadingPart
from studying_light.db.models.review_schedule_item import ReviewScheduleItem
from studying_light.db.models.user_settings import UserSettings
from studying_light.db.session import get_session

router: APIRouter = APIRouter()

DEFAULT_INTERVALS: list[int] = [1, 7, 16, 35, 90]


def _build_review_item_out(
    item: ReviewScheduleItem,
    part: ReadingPart,
    book: Book,
) -> ReviewItemOut:
    """Build review item response."""
    return ReviewItemOut(
        id=item.id,
        reading_part_id=item.reading_part_id,
        interval_days=item.interval_days,
        due_date=item.due_date,
        status=item.status,
        book_id=book.id,
        book_title=book.title,
        part_index=part.part_index,
        label=part.label,
    )


@router.post("/parts", status_code=status.HTTP_201_CREATED)
def create_part(
    payload: ReadingPartCreate,
    session: Session = Depends(get_session),
) -> ReadingPartOut:
    """Create a reading part."""
    book = session.get(Book, payload.book_id)
    if not book:
        raise HTTPException(
            status_code=404,
            detail={"detail": "Book not found", "code": "NOT_FOUND"},
        )

    part_index = payload.part_index
    if part_index is None:
        max_index = session.execute(
            select(func.max(ReadingPart.part_index)).where(
                ReadingPart.book_id == payload.book_id
            )
        ).scalar()
        part_index = (max_index or 0) + 1

    raw_notes = payload.raw_notes.model_dump() if payload.raw_notes else None

    part = ReadingPart(
        book_id=payload.book_id,
        part_index=part_index,
        label=payload.label,
        raw_notes=raw_notes,
        pages_read=payload.pages_read,
        session_seconds=payload.session_seconds,
    )
    session.add(part)
    session.commit()
    session.refresh(part)
    return ReadingPartOut.model_validate(part)


@router.get("/parts")
def list_parts(
    book_id: int | None = None,
    session: Session = Depends(get_session),
) -> list[ReadingPartOut]:
    """List reading parts for a book."""
    if book_id is None:
        raise HTTPException(
            status_code=400,
            detail={"detail": "book_id is required", "code": "BAD_REQUEST"},
        )

    parts = session.execute(
        select(ReadingPart)
        .where(ReadingPart.book_id == book_id)
        .order_by(ReadingPart.part_index)
    ).scalars().all()
    return [ReadingPartOut.model_validate(part) for part in parts]


@router.post("/parts/{part_id}/import_gpt")
def import_gpt(
    part_id: int,
    payload: ImportGptPayload,
    session: Session = Depends(get_session),
) -> ImportGptResponse:
    """Import GPT summary and questions for a reading part."""
    part = session.get(ReadingPart, part_id)
    if not part:
        raise HTTPException(
            status_code=404,
            detail={"detail": "Reading part not found", "code": "NOT_FOUND"},
        )

    part.gpt_summary = payload.gpt_summary
    questions_by_interval = payload.gpt_questions_by_interval.root
    part.gpt_questions_by_interval = questions_by_interval

    existing_items = session.execute(
        select(ReviewScheduleItem).where(ReviewScheduleItem.reading_part_id == part_id)
    ).scalars().all()
    for item in existing_items:
        session.delete(item)

    settings = session.get(UserSettings, 1)
    intervals = settings.intervals_days if settings and settings.intervals_days else []
    if not intervals:
        intervals = DEFAULT_INTERVALS

    base_date = part.created_at.date() if part.created_at else date.today()
    review_items: list[ReviewItemOut] = []
    book = session.get(Book, part.book_id)
    if not book:
        raise HTTPException(
            status_code=404,
            detail={"detail": "Book not found", "code": "NOT_FOUND"},
        )

    try:
        interval_values = [int(value) for value in intervals]
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=422,
            detail={
                "detail": "Invalid intervals configuration",
                "code": "IMPORT_PAYLOAD_INVALID",
            },
        )

    for interval_value in interval_values:
        questions = questions_by_interval.get(interval_value)
        if questions is None:
            questions = questions_by_interval.get(str(interval_value))

        item = ReviewScheduleItem(
            reading_part_id=part.id,
            interval_days=interval_value,
            due_date=base_date + timedelta(days=interval_value),
            status="planned",
            questions=questions,
        )
        session.add(item)
        session.flush()
        review_items.append(_build_review_item_out(item, part, book))

    session.commit()
    session.refresh(part)
    return ImportGptResponse(
        reading_part=ReadingPartOut.model_validate(part),
        review_items=review_items,
    )
