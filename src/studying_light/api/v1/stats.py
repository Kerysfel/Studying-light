"""Stats endpoints."""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from studying_light.api.v1.schemas import ReviewStatsSummaryOut, StatsOverviewOut
from studying_light.db.models.algorithm_review_attempt import AlgorithmReviewAttempt
from studying_light.db.models.algorithm_review_item import AlgorithmReviewItem
from studying_light.db.models.review_attempt import ReviewAttempt
from studying_light.db.models.review_schedule_item import ReviewScheduleItem
from studying_light.db.session import get_session

router: APIRouter = APIRouter()


def _average_rating(
    session: Session,
    rating_column,
    created_column,
    days: int,
) -> float | None:
    since = datetime.now(timezone.utc) - timedelta(days=days)
    value = session.execute(
        select(func.avg(rating_column)).where(
            rating_column.is_not(None),
            created_column >= since,
        )
    ).scalar()
    if value is None:
        return None
    return round(float(value), 2)


@router.get("/stats")
def stats_overview(session: Session = Depends(get_session)) -> StatsOverviewOut:
    """Return aggregated review statistics."""
    theory_average_7d = _average_rating(
        session,
        ReviewAttempt.gpt_rating_1_to_5,
        ReviewAttempt.created_at,
        7,
    )
    theory_average_30d = _average_rating(
        session,
        ReviewAttempt.gpt_rating_1_to_5,
        ReviewAttempt.created_at,
        30,
    )

    algorithm_average_7d = _average_rating(
        session,
        AlgorithmReviewAttempt.rating_1_to_5,
        AlgorithmReviewAttempt.created_at,
        7,
    )
    algorithm_average_30d = _average_rating(
        session,
        AlgorithmReviewAttempt.rating_1_to_5,
        AlgorithmReviewAttempt.created_at,
        30,
    )

    planned_reviews = session.execute(
        select(func.count(ReviewScheduleItem.id)).where(
            ReviewScheduleItem.status == "planned"
        )
    ).scalar()
    completed_reviews = session.execute(
        select(func.count(ReviewScheduleItem.id)).where(
            ReviewScheduleItem.status == "done"
        )
    ).scalar()

    planned_algorithm_reviews = session.execute(
        select(func.count(AlgorithmReviewItem.id)).where(
            AlgorithmReviewItem.status == "planned"
        )
    ).scalar()
    completed_algorithm_reviews = session.execute(
        select(func.count(AlgorithmReviewItem.id)).where(
            AlgorithmReviewItem.status == "done"
        )
    ).scalar()

    return StatsOverviewOut(
        theory=ReviewStatsSummaryOut(
            average_rating_7d=theory_average_7d,
            average_rating_30d=theory_average_30d,
            planned_count=int(planned_reviews or 0),
            completed_count=int(completed_reviews or 0),
        ),
        algorithms=ReviewStatsSummaryOut(
            average_rating_7d=algorithm_average_7d,
            average_rating_30d=algorithm_average_30d,
            planned_count=int(planned_algorithm_reviews or 0),
            completed_count=int(completed_algorithm_reviews or 0),
        ),
    )
