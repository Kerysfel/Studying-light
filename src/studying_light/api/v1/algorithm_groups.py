"""Algorithm group management endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from studying_light.api.v1.schemas import (
    AlgorithmGroupAlgorithmOut,
    AlgorithmGroupCreate,
    AlgorithmGroupDetailOut,
    AlgorithmGroupListOut,
    AlgorithmGroupUpdate,
)
from studying_light.db.models.algorithm import Algorithm
from studying_light.db.models.algorithm_group import AlgorithmGroup, normalize_group_title
from studying_light.db.session import get_session

router: APIRouter = APIRouter()


def _build_group_detail(
    session: Session,
    group: AlgorithmGroup,
) -> AlgorithmGroupDetailOut:
    algorithms = (
        session.execute(
            select(Algorithm)
            .where(Algorithm.group_id == group.id)
            .order_by(Algorithm.id)
        )
        .scalars()
        .all()
    )
    algorithms_out = [
        AlgorithmGroupAlgorithmOut(
            id=algorithm.id,
            title=algorithm.title,
            summary=algorithm.summary,
            complexity=algorithm.complexity,
        )
        for algorithm in algorithms
    ]
    return AlgorithmGroupDetailOut(
        id=group.id,
        title=group.title,
        description=group.description,
        notes=group.notes,
        algorithms_count=len(algorithms_out),
        algorithms=algorithms_out,
    )


@router.get("/algorithm-groups")
def list_algorithm_groups(
    query: str | None = None,
    session: Session = Depends(get_session),
) -> list[AlgorithmGroupListOut]:
    """List algorithm groups with optional title search."""
    counts_subquery = (
        select(
            Algorithm.group_id,
            func.count(Algorithm.id).label("algorithms_count"),
        )
        .group_by(Algorithm.group_id)
        .subquery()
    )
    stmt = (
        select(
            AlgorithmGroup,
            func.coalesce(counts_subquery.c.algorithms_count, 0),
        )
        .outerjoin(counts_subquery, counts_subquery.c.group_id == AlgorithmGroup.id)
        .order_by(AlgorithmGroup.title)
    )

    if query:
        normalized = normalize_group_title(query)
        if normalized:
            stmt = stmt.where(AlgorithmGroup.title_norm.like(f"%{normalized}%"))

    rows = session.execute(stmt).all()
    return [
        AlgorithmGroupListOut(
            id=group.id,
            title=group.title,
            description=group.description,
            notes=group.notes,
            algorithms_count=int(algorithms_count or 0),
        )
        for group, algorithms_count in rows
    ]


@router.get("/algorithm-groups/{group_id}")
def get_algorithm_group(
    group_id: int,
    session: Session = Depends(get_session),
) -> AlgorithmGroupDetailOut:
    """Get algorithm group detail with algorithms list."""
    group = session.get(AlgorithmGroup, group_id)
    if not group:
        raise HTTPException(
            status_code=404,
            detail={"detail": "Algorithm group not found", "code": "NOT_FOUND"},
        )
    return _build_group_detail(session, group)


@router.post("/algorithm-groups", status_code=status.HTTP_201_CREATED)
def create_algorithm_group(
    payload: AlgorithmGroupCreate,
    session: Session = Depends(get_session),
) -> AlgorithmGroupDetailOut:
    """Create an algorithm group."""
    normalized = normalize_group_title(payload.title)
    existing = (
        session.execute(
            select(AlgorithmGroup).where(AlgorithmGroup.title_norm == normalized)
        )
        .scalars()
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=409,
            detail={
                "detail": "Algorithm group already exists",
                "code": "ALGORITHM_GROUP_EXISTS",
            },
        )

    group = AlgorithmGroup(
        title=payload.title.strip(),
        description=payload.description,
        notes=payload.notes,
    )
    session.add(group)
    session.commit()
    session.refresh(group)

    return AlgorithmGroupDetailOut(
        id=group.id,
        title=group.title,
        description=group.description,
        notes=group.notes,
        algorithms_count=0,
        algorithms=[],
    )


@router.patch("/algorithm-groups/{group_id}")
def update_algorithm_group(
    group_id: int,
    payload: AlgorithmGroupUpdate,
    session: Session = Depends(get_session),
) -> AlgorithmGroupDetailOut:
    """Update an algorithm group."""
    group = session.get(AlgorithmGroup, group_id)
    if not group:
        raise HTTPException(
            status_code=404,
            detail={"detail": "Algorithm group not found", "code": "NOT_FOUND"},
        )

    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(
            status_code=400,
            detail={"detail": "No fields provided for update", "code": "BAD_REQUEST"},
        )

    if "title" in updates:
        title_value = updates["title"].strip()
        normalized = normalize_group_title(title_value)
        existing = (
            session.execute(
                select(AlgorithmGroup).where(
                    AlgorithmGroup.title_norm == normalized,
                    AlgorithmGroup.id != group_id,
                )
            )
            .scalars()
            .first()
        )
        if existing:
            raise HTTPException(
                status_code=409,
                detail={
                    "detail": "Algorithm group with this title already exists",
                    "code": "ALGORITHM_GROUP_EXISTS",
                },
            )
        updates["title"] = title_value

    for key, value in updates.items():
        setattr(group, key, value)

    session.commit()
    session.refresh(group)
    return _build_group_detail(session, group)
