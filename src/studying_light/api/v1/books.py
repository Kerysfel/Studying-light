"""Book endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from studying_light.api.v1.schemas import BookCreate, BookStatsOut, BookUpdate
from studying_light.db.models.book import Book
from studying_light.db.models.reading_part import ReadingPart
from studying_light.db.models.review_attempt import ReviewAttempt
from studying_light.db.models.review_schedule_item import ReviewScheduleItem
from studying_light.db.session import get_session

router: APIRouter = APIRouter()


def _collect_book_stats(
    session: Session,
    book_ids: list[int],
) -> tuple[dict[int, int], dict[int, tuple[int, int, int]]]:
    """Collect aggregated reading stats for the given books."""
    if not book_ids:
        return {}, {}

    pages_rows = session.execute(
        select(
            ReadingPart.book_id,
            func.coalesce(func.sum(ReadingPart.pages_read), 0),
        )
        .where(
            ReadingPart.book_id.in_(book_ids),
            ReadingPart.pages_read.is_not(None),
        )
        .group_by(ReadingPart.book_id)
    ).all()
    pages_by_book = {book_id: int(total or 0) for book_id, total in pages_rows}

    stats_rows = session.execute(
        select(
            ReadingPart.book_id,
            func.count(ReadingPart.id),
            func.count(ReadingPart.session_seconds),
            func.coalesce(func.sum(ReadingPart.session_seconds), 0),
        )
        .where(ReadingPart.book_id.in_(book_ids))
        .group_by(ReadingPart.book_id)
    ).all()
    stats_by_book: dict[int, tuple[int, int, int]] = {}
    for book_id, parts_total, sessions_total, seconds_total in stats_rows:
        stats_by_book[int(book_id)] = (
            int(parts_total or 0),
            int(sessions_total or 0),
            int(seconds_total or 0),
        )
    return pages_by_book, stats_by_book


def _build_book_stats_out(
    book: Book,
    pages_by_book: dict[int, int],
    stats_by_book: dict[int, tuple[int, int, int]],
) -> BookStatsOut:
    """Build a book response with stats."""
    parts_total, sessions_total, seconds_total = stats_by_book.get(
        book.id,
        (0, 0, 0),
    )
    if sessions_total == 0 and parts_total > 0:
        sessions_total = parts_total
    return BookStatsOut(
        id=book.id,
        title=book.title,
        author=book.author,
        status=book.status,
        pages_total=book.pages_total,
        pages_read_total=pages_by_book.get(book.id, 0),
        parts_total=parts_total,
        sessions_total=sessions_total,
        reading_seconds_total=seconds_total,
    )


@router.get("/books")
def list_books(session: Session = Depends(get_session)) -> list[BookStatsOut]:
    """List all books."""
    books = session.execute(select(Book).order_by(Book.id)).scalars().all()
    book_ids = [book.id for book in books]
    pages_by_book, stats_by_book = _collect_book_stats(session, book_ids)
    return [
        _build_book_stats_out(book, pages_by_book, stats_by_book) for book in books
    ]


@router.post("/books", status_code=status.HTTP_201_CREATED)
def create_book(
    payload: BookCreate,
    session: Session = Depends(get_session),
) -> BookStatsOut:
    """Create a new book."""
    book = Book(
        title=payload.title,
        author=payload.author,
        status="active",
        pages_total=payload.pages_total,
    )
    session.add(book)
    session.commit()
    session.refresh(book)
    pages_by_book, stats_by_book = _collect_book_stats(session, [book.id])
    return _build_book_stats_out(book, pages_by_book, stats_by_book)


@router.patch("/books/{book_id}")
def update_book(
    book_id: int,
    payload: BookUpdate,
    session: Session = Depends(get_session),
) -> BookStatsOut:
    """Update an existing book."""
    book = session.get(Book, book_id)
    if not book:
        raise HTTPException(
            status_code=404,
            detail={"detail": "Book not found", "code": "NOT_FOUND"},
        )

    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(
            status_code=400,
            detail={"detail": "No fields provided for update", "code": "BAD_REQUEST"},
        )

    status_value = updates.get("status")
    if status_value and status_value not in {"active", "archived"}:
        raise HTTPException(
            status_code=422,
            detail={"detail": "Invalid status value", "code": "VALIDATION_ERROR"},
        )

    for key, value in updates.items():
        setattr(book, key, value)

    session.commit()
    session.refresh(book)
    pages_by_book, stats_by_book = _collect_book_stats(session, [book.id])
    return _build_book_stats_out(book, pages_by_book, stats_by_book)


@router.delete("/books/{book_id}")
def delete_book(book_id: int, session: Session = Depends(get_session)) -> dict[str, str]:
    """Delete a book."""
    book = session.get(Book, book_id)
    if not book:
        raise HTTPException(
            status_code=404,
            detail={"detail": "Book not found", "code": "NOT_FOUND"},
        )

    part_ids = session.execute(
        select(ReadingPart.id).where(ReadingPart.book_id == book_id)
    ).scalars().all()
    if part_ids:
        review_item_ids = session.execute(
            select(ReviewScheduleItem.id).where(
                ReviewScheduleItem.reading_part_id.in_(part_ids)
            )
        ).scalars().all()
        if review_item_ids:
            session.execute(
                delete(ReviewAttempt).where(
                    ReviewAttempt.review_item_id.in_(review_item_ids)
                )
            )
            session.execute(
                delete(ReviewScheduleItem).where(
                    ReviewScheduleItem.id.in_(review_item_ids)
                )
            )
        session.execute(delete(ReadingPart).where(ReadingPart.id.in_(part_ids)))

    session.delete(book)
    session.commit()
    return {"status": "deleted"}
