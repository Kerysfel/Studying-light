"""Review endpoints."""

import json
from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from studying_light.api.v1.schemas import (
    ReviewAttemptOut,
    ReviewCompletePayload,
    ReviewDetailOut,
    ReviewFeedbackPayload,
    ReviewItemOut,
    ReviewPartStatsOut,
    ReviewScheduleItemOut,
    ReviewScheduleUpdatePayload,
)
from studying_light.api.v1.structures import GptReviewItem
from studying_light.db.models.book import Book
from studying_light.db.models.reading_part import ReadingPart
from studying_light.db.models.review_attempt import ReviewAttempt
from studying_light.db.models.review_schedule_item import ReviewScheduleItem
from studying_light.db.session import get_session

router: APIRouter = APIRouter()


def _compute_overall_metrics(items: list[GptReviewItem]) -> tuple[int, int, str]:
    """Compute overall rating, score, and verdict from item ratings."""
    if not items:
        return 1, 20, "FAIL"
    total = sum(item.rating_1_to_5 for item in items)
    average = total / len(items)
    rating = int(average + 0.5)
    rating = min(max(rating, 1), 5)
    score = int(round((rating / 5) * 100))
    if rating >= 4:
        verdict = "PASS"
    elif rating == 3:
        verdict = "PARTIAL"
    else:
        verdict = "FAIL"
    return rating, score, verdict


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
    """List planned review items, including overdue ones."""
    rows = session.execute(
        select(ReviewScheduleItem, ReadingPart, Book)
        .join(ReadingPart, ReviewScheduleItem.reading_part_id == ReadingPart.id)
        .join(Book, ReadingPart.book_id == Book.id)
        .where(
            ReviewScheduleItem.status == "planned",
        )
        .order_by(ReviewScheduleItem.due_date, ReviewScheduleItem.id)
    ).all()

    return [_build_review_item_out(item, part, book) for item, part, book in rows]


@router.get("/reviews/schedule")
def review_schedule(
    reading_part_id: int | None = None,
    session: Session = Depends(get_session),
) -> list[ReviewScheduleItemOut]:
    """List scheduled review items for a reading part."""
    if reading_part_id is None:
        raise HTTPException(
            status_code=400,
            detail={"detail": "reading_part_id is required", "code": "BAD_REQUEST"},
        )

    today = date.today()
    items = (
        session.execute(
            select(ReviewScheduleItem)
            .where(
                ReviewScheduleItem.reading_part_id == reading_part_id,
                ReviewScheduleItem.status == "planned",
                ReviewScheduleItem.due_date >= today,
            )
            .order_by(ReviewScheduleItem.due_date)
        )
        .scalars()
        .all()
    )

    return [
        ReviewScheduleItemOut(
            id=item.id,
            reading_part_id=item.reading_part_id,
            interval_days=item.interval_days,
            due_date=item.due_date,
            status=item.status,
        )
        for item in items
    ]


@router.patch("/reviews/{review_id}")
def update_review_schedule(
    review_id: int,
    payload: ReviewScheduleUpdatePayload,
    session: Session = Depends(get_session),
) -> ReviewScheduleItemOut:
    """Update a planned review schedule item."""
    review_item = session.get(ReviewScheduleItem, review_id)
    if not review_item:
        raise HTTPException(
            status_code=404,
            detail={"detail": "Review item not found", "code": "NOT_FOUND"},
        )
    if review_item.status != "planned":
        raise HTTPException(
            status_code=409,
            detail={
                "detail": "Only planned reviews can be rescheduled",
                "code": "CONFLICT",
            },
        )
    if payload.due_date < date.today():
        raise HTTPException(
            status_code=422,
            detail={
                "detail": "due_date must be today or later",
                "code": "VALIDATION_ERROR",
            },
        )

    review_item.due_date = payload.due_date
    session.commit()
    session.refresh(review_item)
    return ReviewScheduleItemOut(
        id=review_item.id,
        reading_part_id=review_item.reading_part_id,
        interval_days=review_item.interval_days,
        due_date=review_item.due_date,
        status=review_item.status,
    )


@router.get("/reviews/stats")
def review_stats(session: Session = Depends(get_session)) -> list[ReviewPartStatsOut]:
    """Return review completion statistics per reading part."""
    rows = session.execute(
        select(
            ReadingPart.id,
            ReadingPart.part_index,
            ReadingPart.label,
            ReadingPart.gpt_summary,
            Book.id,
            Book.title,
            func.count(ReviewScheduleItem.id),
            func.coalesce(
                func.sum(case((ReviewScheduleItem.status == "done", 1), else_=0)),
                0,
            ),
        )
        .join(Book, ReadingPart.book_id == Book.id)
        .outerjoin(
            ReviewScheduleItem,
            ReviewScheduleItem.reading_part_id == ReadingPart.id,
        )
        .group_by(
            ReadingPart.id,
            ReadingPart.part_index,
            ReadingPart.label,
            ReadingPart.gpt_summary,
            Book.id,
            Book.title,
        )
        .order_by(Book.id, ReadingPart.part_index)
    ).all()

    gpt_rows = session.execute(
        select(
            ReadingPart.id,
            func.count(ReviewAttempt.id),
            func.avg(ReviewAttempt.gpt_rating_1_to_5),
        )
        .join(Book, ReadingPart.book_id == Book.id)
        .join(
            ReviewScheduleItem,
            ReviewScheduleItem.reading_part_id == ReadingPart.id,
        )
        .join(
            ReviewAttempt,
            ReviewAttempt.review_item_id == ReviewScheduleItem.id,
        )
        .where(ReviewAttempt.gpt_rating_1_to_5.is_not(None))
        .group_by(ReadingPart.id)
    ).all()
    gpt_stats: dict[int, tuple[int, float | None]] = {}
    for part_id, attempts_total, average_rating in gpt_rows:
        average_value = float(average_rating) if average_rating is not None else None
        if average_value is not None:
            average_value = round(average_value, 2)
        gpt_stats[int(part_id)] = (int(attempts_total or 0), average_value)

    return [
        ReviewPartStatsOut(
            reading_part_id=part_id,
            book_id=book_id,
            book_title=book_title,
            part_index=part_index,
            label=label,
            summary=summary,
            total_reviews=int(total_reviews or 0),
            completed_reviews=int(completed_reviews or 0),
            gpt_attempts_total=gpt_stats.get(int(part_id), (0, None))[0],
            gpt_average_rating=gpt_stats.get(int(part_id), (0, None))[1],
        )
        for (
            part_id,
            part_index,
            label,
            summary,
            book_id,
            book_title,
            total_reviews,
            completed_reviews,
        ) in rows
    ]


@router.get("/reviews/{review_id}")
def review_detail(
    review_id: int,
    session: Session = Depends(get_session),
) -> ReviewDetailOut:
    """Return review details with summary, notes, and questions."""
    review_item = session.get(ReviewScheduleItem, review_id)
    if not review_item:
        raise HTTPException(
            status_code=404,
            detail={"detail": "Review item not found", "code": "NOT_FOUND"},
        )

    part = session.get(ReadingPart, review_item.reading_part_id)
    book = session.get(Book, part.book_id) if part else None
    if not part or not book:
        raise HTTPException(
            status_code=404,
            detail={"detail": "Related book or part not found", "code": "NOT_FOUND"},
        )

    questions = review_item.questions or []
    if not isinstance(questions, list) or any(
        not isinstance(item, str) for item in questions
    ):
        raise HTTPException(
            status_code=422,
            detail={
                "detail": "Некорректный формат вопросов",
                "code": "VALIDATION_ERROR",
            },
        )

    attempt = session.execute(
        select(ReviewAttempt)
        .where(ReviewAttempt.review_item_id == review_item.id)
        .order_by(ReviewAttempt.created_at.desc())
        .limit(1)
    ).scalar_one_or_none()

    gpt_feedback = None
    if attempt and attempt.gpt_check_payload:
        gpt_feedback = attempt.gpt_check_payload

    return ReviewDetailOut(
        id=review_item.id,
        reading_part_id=review_item.reading_part_id,
        interval_days=review_item.interval_days,
        due_date=review_item.due_date,
        status=review_item.status,
        book_id=book.id,
        book_title=book.title,
        part_index=part.part_index,
        label=part.label,
        summary=part.gpt_summary,
        raw_notes=part.raw_notes,
        questions=questions,
        gpt_feedback=gpt_feedback,
    )


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

    gpt_payload = payload.gpt_check_result.model_dump(mode="json")
    rating, score, verdict = _compute_overall_metrics(payload.gpt_check_result.items)
    attempt.gpt_check_result = json.dumps(gpt_payload, ensure_ascii=False)
    attempt.gpt_check_payload = gpt_payload
    attempt.gpt_rating_1_to_5 = rating
    attempt.gpt_score_0_to_100 = score
    attempt.gpt_verdict = verdict
    session.commit()
    session.refresh(attempt)

    return ReviewAttemptOut(
        id=attempt.id,
        review_item_id=attempt.review_item_id,
        created_at=attempt.created_at,
        gpt_check_result=attempt.gpt_check_result,
        gpt_check_payload=attempt.gpt_check_payload,
        gpt_rating_1_to_5=attempt.gpt_rating_1_to_5,
        gpt_score_0_to_100=attempt.gpt_score_0_to_100,
        gpt_verdict=attempt.gpt_verdict,
    )
