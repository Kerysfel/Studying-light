"""Algorithm training endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from studying_light.api.v1.schemas import (
    AlgorithmTrainingAttemptOut,
    AlgorithmTrainingCreate,
)
from studying_light.db.models.algorithm import Algorithm
from studying_light.db.models.algorithm_training_attempt import AlgorithmTrainingAttempt
from studying_light.db.session import get_session

router: APIRouter = APIRouter()


def _build_training_out(attempt: AlgorithmTrainingAttempt) -> AlgorithmTrainingAttemptOut:
    return AlgorithmTrainingAttemptOut(
        id=attempt.id,
        algorithm_id=attempt.algorithm_id,
        mode=attempt.mode,
        code_text=attempt.code_text,
        gpt_check_json=attempt.gpt_check_json,
        rating_1_to_5=attempt.rating_1_to_5,
        accuracy=attempt.accuracy,
        duration_sec=attempt.duration_sec,
        created_at=attempt.created_at,
    )


@router.post("/algorithm-trainings", status_code=status.HTTP_201_CREATED)
def create_algorithm_training(
    payload: AlgorithmTrainingCreate,
    session: Session = Depends(get_session),
) -> AlgorithmTrainingAttemptOut:
    """Create a training attempt for an algorithm."""
    algorithm = session.get(Algorithm, payload.algorithm_id)
    if not algorithm:
        raise HTTPException(
            status_code=404,
            detail={"detail": "Algorithm not found", "code": "NOT_FOUND"},
        )

    gpt_payload = (
        payload.gpt_check_result.model_dump(mode="json")
        if payload.gpt_check_result
        else None
    )
    rating = (
        payload.gpt_check_result.overall.rating_1_to_5
        if payload.gpt_check_result
        else None
    )

    attempt = AlgorithmTrainingAttempt(
        algorithm_id=payload.algorithm_id,
        mode=payload.mode,
        code_text=payload.code_text,
        gpt_check_json=gpt_payload,
        rating_1_to_5=rating,
        accuracy=payload.accuracy,
        duration_sec=payload.duration_sec,
    )
    session.add(attempt)
    session.commit()
    session.refresh(attempt)

    return _build_training_out(attempt)


@router.get("/algorithm-trainings")
def list_algorithm_trainings(
    algorithm_id: int | None = None,
    session: Session = Depends(get_session),
) -> list[AlgorithmTrainingAttemptOut]:
    """List training attempts for an algorithm."""
    if algorithm_id is None:
        raise HTTPException(
            status_code=400,
            detail={"detail": "algorithm_id is required", "code": "BAD_REQUEST"},
        )

    rows = (
        session.execute(
            select(AlgorithmTrainingAttempt)
            .where(AlgorithmTrainingAttempt.algorithm_id == algorithm_id)
            .order_by(AlgorithmTrainingAttempt.created_at.desc())
        )
        .scalars()
        .all()
    )

    return [_build_training_out(item) for item in rows]
