"""Review endpoints."""

from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from studying_light.api.v1.schemas import (
    ReviewAttemptOut,
    ReviewCompletePayload,
    ReviewFeedbackPayload,
    ReviewItemOut,
)
from studying_light.db.models.book import Book
from studying_light.db.models.reading_part import ReadingPart
from studying_light.db.models.review_attempt import ReviewAttempt
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


@router.get("/reviews/today")
def reviews_today(session: Session = Depends(get_session)) -> list[ReviewItemOut]:
    """List review items due today."""
    today = date.today()
    rows = session.execute(
        select(ReviewScheduleItem, ReadingPart, Book)
        .join(ReadingPart, ReviewScheduleItem.reading_part_id == ReadingPart.id)
        .join(Book, ReadingPart.book_id == Book.id)
        .where(
            ReviewScheduleItem.due_date == today,
            ReviewScheduleItem.status == "planned",
        )
        .order_by(ReviewScheduleItem.id)
    ).all()

    return [_build_review_item_out(item, part, book) for item, part, book in rows]


@router.post("/reviews/{review_id}/complete")
def complete_review(
    review_id: int,
    payload: ReviewCompletePayload,
    session: Session = Depends(get_session),
) -> ReviewItemOut:
    """Complete a review item."""
    review_item = session.get(ReviewScheduleItem, review_id)
    if not review_item:
        raise HTTPException(
            status_code=404,
            detail={"detail": "Review item not found", "code": "NOT_FOUND"},
        )

    review_item.status = "done"
    review_item.completed_at = datetime.now(timezone.utc)

    attempt = ReviewAttempt(review_item_id=review_id, answers=payload.answers)
    session.add(attempt)
    session.commit()

    part = session.get(ReadingPart, review_item.reading_part_id)
    book = session.get(Book, part.book_id) if part else None
    if not part or not book:
        raise HTTPException(
            status_code=404,
            detail={"detail": "Related book or part not found", "code": "NOT_FOUND"},
        )

    return _build_review_item_out(review_item, part, book)


@router.post("/reviews/{review_id}/save_gpt_feedback")
def save_gpt_feedback(
    review_id: int,
    payload: ReviewFeedbackPayload,
    session: Session = Depends(get_session),
) -> ReviewAttemptOut:
    """Save GPT feedback for a review."""
    review_item = session.get(ReviewScheduleItem, review_id)
    if not review_item:
        raise HTTPException(
            status_code=404,
            detail={"detail": "Review item not found", "code": "NOT_FOUND"},
        )

    attempt = session.execute(
        select(ReviewAttempt)
        .where(ReviewAttempt.review_item_id == review_id)
        .order_by(ReviewAttempt.created_at.desc())
        .limit(1)
    ).scalar_one_or_none()

    if attempt is None:
        attempt = ReviewAttempt(review_item_id=review_id, answers={})
        session.add(attempt)

    attempt.gpt_check_result = payload.gpt_check_result
    session.commit()
    session.refresh(attempt)

    return ReviewAttemptOut(
        id=attempt.id,
        review_item_id=attempt.review_item_id,
        created_at=attempt.created_at,
        gpt_check_result=attempt.gpt_check_result,
    )
