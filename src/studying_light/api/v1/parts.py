"""Reading part endpoints."""

from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from studying_light.api.v1.deps import get_optional_user
from studying_light.api.v1.schemas import (
    ImportGptPayload,
    ImportGptResponse,
    ReadingPartCreate,
    ReadingPartOut,
    ReviewItemOut,
)
from studying_light.db.models.book import Book
from studying_light.db.models.reading_part import ReadingPart
from studying_light.db.models.review_schedule_item import ReviewScheduleItem
from studying_light.db.models.user_settings import UserSettings
from studying_light.db.models.user import User
from studying_light.db.session import get_session
from studying_light.services.user_settings import DEFAULT_SETTINGS

router: APIRouter = APIRouter()

DEFAULT_INTERVALS: list[int] = DEFAULT_SETTINGS["intervals_days"]


def _compute_pages_read(
    session: Session,
    book_id: int,
    part_index: int,
    page_end: int,
) -> int:
    """Compute pages read based on the last saved page."""
    last_end = session.execute(
        select(ReadingPart.page_end)
        .where(
            ReadingPart.book_id == book_id,
            ReadingPart.page_end.is_not(None),
            ReadingPart.part_index < part_index,
        )
        .order_by(ReadingPart.part_index.desc())
        .limit(1)
    ).scalar_one_or_none()

    if last_end is None:
        return page_end

    if page_end < last_end:
        raise HTTPException(
            status_code=422,
            detail={
                "detail": "page_end must be greater than or equal to last saved page",
                "code": "PAGE_END_INVALID",
            },
        )

    return page_end - last_end


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
    pages_read_value = payload.pages_read
    page_end_value = payload.page_end
    if page_end_value is not None:
        pages_read_value = _compute_pages_read(
            session,
            payload.book_id,
            part_index,
            page_end_value,
        )

    part = ReadingPart(
        book_id=payload.book_id,
        part_index=part_index,
        label=payload.label,
        raw_notes=raw_notes,
        pages_read=pages_read_value,
        session_seconds=payload.session_seconds,
        page_end=page_end_value,
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

    parts = (
        session.execute(
            select(ReadingPart)
            .where(ReadingPart.book_id == book_id)
            .order_by(ReadingPart.part_index)
        )
        .scalars()
        .all()
    )
    return [ReadingPartOut.model_validate(part) for part in parts]


@router.post("/parts/{part_id}/import_gpt")
def import_gpt(
    part_id: int,
    payload: ImportGptPayload,
    session: Session = Depends(get_session),
    current_user: User | None = Depends(get_optional_user),
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

    existing_items = (
        session.execute(
            select(ReviewScheduleItem).where(
                ReviewScheduleItem.reading_part_id == part_id
            )
        )
        .scalars()
        .all()
    )
    for item in existing_items:
        session.delete(item)

    settings = None
    if current_user:
        settings = session.get(UserSettings, current_user.id)
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
    except (TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=422,
            detail={
                "detail": "Invalid intervals configuration",
                "code": "IMPORT_PAYLOAD_INVALID",
            },
        ) from exc

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
