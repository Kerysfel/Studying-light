"""Algorithm review endpoints."""

from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from studying_light.api.v1.deps import get_current_user
from studying_light.api.v1.schemas import (
    AlgorithmReviewAttemptOut,
    AlgorithmReviewCompletePayload,
    AlgorithmReviewDetailOut,
    AlgorithmReviewFeedbackPayload,
    AlgorithmReviewItemOut,
    AlgorithmReviewStatsOut,
)
from studying_light.db.models.algorithm import Algorithm
from studying_light.db.models.algorithm_group import AlgorithmGroup
from studying_light.db.models.algorithm_review_attempt import AlgorithmReviewAttempt
from studying_light.db.models.algorithm_review_item import AlgorithmReviewItem
from studying_light.db.models.user import User
from studying_light.db.session import get_session

router: APIRouter = APIRouter()


def _build_algorithm_review_item_out(
    item: AlgorithmReviewItem,
    algorithm: Algorithm,
    group: AlgorithmGroup,
    gpt_rating_1_to_5: int | None = None,
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
        gpt_rating_1_to_5=gpt_rating_1_to_5,
    )


@router.get("/algorithm-reviews/today")
def algorithm_reviews_today(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> list[AlgorithmReviewItemOut]:
    """List planned algorithm review items scheduled for today or later."""
    today = date.today()
    latest_rating = (
        select(AlgorithmReviewAttempt.rating_1_to_5)
        .where(
            AlgorithmReviewAttempt.review_item_id == AlgorithmReviewItem.id,
            AlgorithmReviewAttempt.user_id == current_user.id,
        )
        .order_by(AlgorithmReviewAttempt.created_at.desc())
        .limit(1)
        .scalar_subquery()
    )
    rows = session.execute(
        select(AlgorithmReviewItem, Algorithm, AlgorithmGroup, latest_rating)
        .join(Algorithm, AlgorithmReviewItem.algorithm_id == Algorithm.id)
        .join(AlgorithmGroup, Algorithm.group_id == AlgorithmGroup.id)
        .where(
            AlgorithmReviewItem.status == "planned",
            AlgorithmReviewItem.due_date >= today,
            AlgorithmReviewItem.user_id == current_user.id,
        )
        .order_by(AlgorithmReviewItem.due_date, AlgorithmReviewItem.id)
    ).all()

    return [
        _build_algorithm_review_item_out(item, algorithm, group, rating)
        for item, algorithm, group, rating in rows
    ]


@router.get("/algorithm-reviews/stats")
def algorithm_review_stats(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> list[AlgorithmReviewStatsOut]:
    """Return algorithm review statistics per algorithm."""
    rows = session.execute(
        select(
            AlgorithmGroup.id,
            AlgorithmGroup.title,
            Algorithm.id,
            Algorithm.title,
            func.count(AlgorithmReviewItem.id),
            func.coalesce(
                func.sum(case((AlgorithmReviewItem.status == "done", 1), else_=0)),
                0,
            ),
        )
        .join(AlgorithmGroup, Algorithm.group_id == AlgorithmGroup.id)
        .outerjoin(
            AlgorithmReviewItem,
            AlgorithmReviewItem.algorithm_id == Algorithm.id,
        )
        .where(
            AlgorithmGroup.user_id == current_user.id,
            Algorithm.user_id == current_user.id,
        )
        .group_by(
            AlgorithmGroup.id,
            AlgorithmGroup.title,
            Algorithm.id,
            Algorithm.title,
        )
        .order_by(AlgorithmGroup.id, Algorithm.id)
    ).all()

    gpt_rows = session.execute(
        select(
            Algorithm.id,
            func.count(AlgorithmReviewAttempt.id),
            func.avg(AlgorithmReviewAttempt.rating_1_to_5),
        )
        .join(
            AlgorithmReviewItem,
            AlgorithmReviewItem.algorithm_id == Algorithm.id,
        )
        .join(
            AlgorithmReviewAttempt,
            AlgorithmReviewAttempt.review_item_id == AlgorithmReviewItem.id,
        )
        .where(AlgorithmReviewAttempt.rating_1_to_5.is_not(None))
        .where(
            Algorithm.user_id == current_user.id,
            AlgorithmReviewItem.user_id == current_user.id,
            AlgorithmReviewAttempt.user_id == current_user.id,
        )
        .group_by(Algorithm.id)
    ).all()

    gpt_stats: dict[int, tuple[int, float | None]] = {}
    for algorithm_id, attempts_total, average_rating in gpt_rows:
        average_value = float(average_rating) if average_rating is not None else None
        if average_value is not None:
            average_value = round(average_value, 2)
        gpt_stats[int(algorithm_id)] = (int(attempts_total or 0), average_value)

    return [
        AlgorithmReviewStatsOut(
            group_id=int(group_id),
            group_title=group_title,
            algorithm_id=int(algorithm_id),
            algorithm_title=algorithm_title,
            total_reviews=int(total_reviews or 0),
            completed_reviews=int(completed_reviews or 0),
            gpt_attempts_total=gpt_stats.get(int(algorithm_id), (0, None))[0],
            gpt_average_rating=gpt_stats.get(int(algorithm_id), (0, None))[1],
        )
        for (
            group_id,
            group_title,
            algorithm_id,
            algorithm_title,
            total_reviews,
            completed_reviews,
        ) in rows
    ]


@router.get("/algorithm-reviews/{review_id}")
def algorithm_review_detail(
    review_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> AlgorithmReviewDetailOut:
    """Return algorithm review detail."""
    row = session.execute(
        select(AlgorithmReviewItem, Algorithm, AlgorithmGroup)
        .join(Algorithm, AlgorithmReviewItem.algorithm_id == Algorithm.id)
        .join(AlgorithmGroup, Algorithm.group_id == AlgorithmGroup.id)
        .where(
            AlgorithmReviewItem.id == review_id,
            AlgorithmReviewItem.user_id == current_user.id,
            Algorithm.user_id == current_user.id,
            AlgorithmGroup.user_id == current_user.id,
        )
        .limit(1)
    ).first()

    if not row:
        raise HTTPException(
            status_code=404,
            detail={"detail": "Algorithm review item not found", "code": "NOT_FOUND"},
        )

    review_item, algorithm, group = row
    attempt = session.execute(
        select(AlgorithmReviewAttempt)
        .where(
            AlgorithmReviewAttempt.review_item_id == review_id,
            AlgorithmReviewAttempt.user_id == current_user.id,
        )
        .order_by(AlgorithmReviewAttempt.created_at.desc())
        .limit(1)
    ).scalar_one_or_none()

    return AlgorithmReviewDetailOut(
        id=review_item.id,
        algorithm_id=review_item.algorithm_id,
        interval_days=review_item.interval_days,
        due_date=review_item.due_date,
        status=review_item.status,
        group_id=group.id,
        group_title=group.title,
        title=algorithm.title,
        summary=algorithm.summary,
        when_to_use=algorithm.when_to_use,
        complexity=algorithm.complexity,
        invariants=algorithm.invariants,
        steps=algorithm.steps,
        corner_cases=algorithm.corner_cases,
        questions=review_item.questions or [],
        gpt_feedback=attempt.gpt_check_json if attempt else None,
    )


@router.post("/algorithm-reviews/{review_id}/complete")
def complete_algorithm_review(
    review_id: int,
    payload: AlgorithmReviewCompletePayload,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> AlgorithmReviewItemOut:
    """Complete an algorithm review item."""
    review_item = session.execute(
        select(AlgorithmReviewItem).where(
            AlgorithmReviewItem.id == review_id,
            AlgorithmReviewItem.user_id == current_user.id,
        )
    ).scalar_one_or_none()
    if not review_item:
        raise HTTPException(
            status_code=404,
            detail={"detail": "Algorithm review item not found", "code": "NOT_FOUND"},
        )

    review_item.status = "done"
    review_item.completed_at = datetime.now(timezone.utc)

    attempt = AlgorithmReviewAttempt(
        user_id=current_user.id,
        review_item_id=review_id,
        answers=payload.answers,
    )
    session.add(attempt)
    session.commit()

    algorithm = session.execute(
        select(Algorithm).where(
            Algorithm.id == review_item.algorithm_id,
            Algorithm.user_id == current_user.id,
        )
    ).scalar_one_or_none()
    group = (
        session.execute(
            select(AlgorithmGroup).where(
                AlgorithmGroup.id == algorithm.group_id,
                AlgorithmGroup.user_id == current_user.id,
            )
        ).scalar_one_or_none()
        if algorithm
        else None
    )
    if not algorithm or not group:
        raise HTTPException(
            status_code=404,
            detail={
                "detail": "Related algorithm or group not found",
                "code": "NOT_FOUND",
            },
        )

    return _build_algorithm_review_item_out(review_item, algorithm, group)


@router.post("/algorithm-reviews/{review_id}/save_gpt_feedback")
def save_algorithm_gpt_feedback(
    review_id: int,
    payload: AlgorithmReviewFeedbackPayload,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> AlgorithmReviewAttemptOut:
    """Save GPT feedback for an algorithm review."""
    review_item = session.execute(
        select(AlgorithmReviewItem).where(
            AlgorithmReviewItem.id == review_id,
            AlgorithmReviewItem.user_id == current_user.id,
        )
    ).scalar_one_or_none()
    if not review_item:
        raise HTTPException(
            status_code=404,
            detail={"detail": "Algorithm review item not found", "code": "NOT_FOUND"},
        )

    attempt = session.execute(
        select(AlgorithmReviewAttempt)
        .where(
            AlgorithmReviewAttempt.review_item_id == review_id,
            AlgorithmReviewAttempt.user_id == current_user.id,
        )
        .order_by(AlgorithmReviewAttempt.created_at.desc())
        .limit(1)
    ).scalar_one_or_none()

    if attempt is None:
        attempt = AlgorithmReviewAttempt(
            user_id=current_user.id,
            review_item_id=review_id,
            answers={},
        )
        session.add(attempt)

    gpt_payload = payload.gpt_check_result.model_dump(mode="json")
    attempt.gpt_check_json = gpt_payload
    attempt.rating_1_to_5 = payload.gpt_check_result.overall.rating_1_to_5
    session.commit()
    session.refresh(attempt)

    return AlgorithmReviewAttemptOut(
        id=attempt.id,
        review_item_id=attempt.review_item_id,
        created_at=attempt.created_at,
        gpt_check_json=gpt_payload,
        rating_1_to_5=attempt.rating_1_to_5,
    )
