"""Dashboard endpoints."""

from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from studying_light.api.v1.schemas import (
    AlgorithmReviewItemOut,
    BookProgressOut,
    ReviewItemOut,
    ReviewProgressOut,
    TodayResponse,
)
from studying_light.db.models.algorithm import Algorithm
from studying_light.db.models.algorithm_group import AlgorithmGroup
from studying_light.db.models.algorithm_review_item import AlgorithmReviewItem
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


def _build_algorithm_review_item_out(
    item: AlgorithmReviewItem,
    algorithm: Algorithm,
    group: AlgorithmGroup,
) -> AlgorithmReviewItemOut:
    """Build algorithm review item response."""
    return AlgorithmReviewItemOut(
        id=item.id,
        algorithm_id=item.algorithm_id,
        interval_days=item.interval_days,
        due_date=item.due_date,
        status=item.status,
        group_id=group.id,
        group_title=group.title,
        title=algorithm.title,
    )


@router.get("/today")
def today(session: Session = Depends(get_session)) -> TodayResponse:
    """Return today's reading plan and reviews."""
    active_books = session.execute(
        select(Book).where(Book.status == "active").order_by(Book.id)
    ).scalars().all()

    book_ids = [book.id for book in active_books]
    pages_by_book: dict[int, int] = {}
    if book_ids:
        pages_rows = session.execute(
            select(
                ReadingPart.book_id,
                func.coalesce(
                    func.max(ReadingPart.page_end),
                    func.sum(ReadingPart.pages_read),
                    0,
                ),
            )
            .where(ReadingPart.book_id.in_(book_ids))
            .group_by(ReadingPart.book_id)
        ).all()
        pages_by_book = {book_id: int(total or 0) for book_id, total in pages_rows}

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

    algorithm_review_rows = session.execute(
        select(AlgorithmReviewItem, Algorithm, AlgorithmGroup)
        .join(Algorithm, AlgorithmReviewItem.algorithm_id == Algorithm.id)
        .join(AlgorithmGroup, Algorithm.group_id == AlgorithmGroup.id)
        .where(
            AlgorithmReviewItem.due_date == date.today(),
            AlgorithmReviewItem.status == "planned",
        )
        .order_by(AlgorithmReviewItem.id)
    ).all()

    algorithm_review_items = [
        _build_algorithm_review_item_out(item, algorithm, group)
        for item, algorithm, group in algorithm_review_rows
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
        algorithm_review_items=algorithm_review_items,
        review_progress=ReviewProgressOut(
            total=int(review_total or 0),
            completed=int(review_completed or 0),
        ),
    )
