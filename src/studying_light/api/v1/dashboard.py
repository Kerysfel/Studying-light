"""Dashboard endpoints."""

from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from studying_light.api.v1.schemas import (
    BookProgressOut,
    ReviewItemOut,
    ReviewProgressOut,
    TodayResponse,
)
from studying_light.db.models.book import Book
from studying_light.db.models.reading_part import ReadingPart
from studying_light.db.models.review_schedule_item import ReviewScheduleItem
from studying_light.db.session import get_session

router: APIRouter = APIRouter()


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


@router.get("/today")
def today(session: Session = Depends(get_session)) -> TodayResponse:
    """Return today's reading plan and reviews."""
    active_books = session.execute(
        select(Book).where(Book.status == "active").order_by(Book.id)
    ).scalars().all()

    pages_rows = session.execute(
        select(
            ReadingPart.book_id,
            func.coalesce(func.sum(ReadingPart.pages_read), 0),
        )
        .where(ReadingPart.pages_read.is_not(None))
        .group_by(ReadingPart.book_id)
    ).all()
    pages_by_book = {book_id: total for book_id, total in pages_rows}

    review_rows = session.execute(
        select(ReviewScheduleItem, ReadingPart, Book)
        .join(ReadingPart, ReviewScheduleItem.reading_part_id == ReadingPart.id)
        .join(Book, ReadingPart.book_id == Book.id)
        .where(
            ReviewScheduleItem.due_date == date.today(),
            ReviewScheduleItem.status == "planned",
        )
        .order_by(ReviewScheduleItem.id)
    ).all()

    review_items = [
        _build_review_item_out(item, part, book)
        for item, part, book in review_rows
    ]

    review_total = session.execute(
        select(func.count(ReviewScheduleItem.id))
    ).scalar()
    review_completed = session.execute(
        select(func.count(ReviewScheduleItem.id)).where(
            ReviewScheduleItem.status == "done"
        )
    ).scalar()

    return TodayResponse(
        active_books=[
            BookProgressOut(
                id=book.id,
                title=book.title,
                author=book.author,
                status=book.status,
                pages_total=book.pages_total,
                pages_read_total=int(pages_by_book.get(book.id, 0)),
            )
            for book in active_books
        ],
        review_items=review_items,
        review_progress=ReviewProgressOut(
            total=int(review_total or 0),
            completed=int(review_completed or 0),
        ),
    )
