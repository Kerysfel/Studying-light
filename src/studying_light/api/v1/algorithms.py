"""Algorithm endpoints."""

import logging
from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from studying_light.api.v1.schemas import (
    AlgorithmCodeSnippetOut,
    AlgorithmDetailOut,
    AlgorithmImportPayload,
    AlgorithmImportResponse,
    AlgorithmListOut,
    ReadingPartOut,
)
from studying_light.db.models.algorithm import Algorithm
from studying_light.db.models.algorithm_code_snippet import AlgorithmCodeSnippet
from studying_light.db.models.algorithm_group import (
    AlgorithmGroup,
    normalize_group_title,
)
from studying_light.db.models.algorithm_review_item import AlgorithmReviewItem
from studying_light.db.models.reading_part import ReadingPart
from studying_light.db.session import get_session

logger = logging.getLogger(__name__)

router: APIRouter = APIRouter()

DEFAULT_INTERVALS: list[int] = [1, 7, 16, 35, 90]


def get_or_create_group(
    session: Session,
    title: str,
    *,
    description: str | None = None,
    notes: str | None = None,
    cache: dict[str, AlgorithmGroup] | None = None,
) -> tuple[AlgorithmGroup, bool]:
    """Fetch a group by normalized title or create it once."""
    normalized = normalize_group_title(title)
    if cache is not None:
        cached = cache.get(normalized)
        if cached is not None:
            return cached, False

    existing = (
        session.execute(
            select(AlgorithmGroup).where(AlgorithmGroup.title_norm == normalized)
        )
        .scalars()
        .first()
    )
    if existing is not None:
        if cache is not None:
            cache[normalized] = existing
        return existing, False

    group = AlgorithmGroup(
        title=title.strip(),
        description=description,
        notes=notes,
    )
    session.add(group)
    session.flush()
    if cache is not None:
        cache[normalized] = group
    return group, True


def _get_questions_for_interval(
    questions_by_interval: dict,
    interval_days: int,
) -> list[str] | None:
    """Get normalized questions for a given interval."""
    questions = questions_by_interval.get(interval_days)
    if questions is None:
        questions = questions_by_interval.get(str(interval_days))
    if not isinstance(questions, list):
        return None
    normalized = [str(item).strip() for item in questions if str(item).strip()]
    return normalized or None


@router.get("/algorithms")
def list_algorithms(
    group_id: int,
    session: Session = Depends(get_session),
) -> list[AlgorithmListOut]:
    """List algorithms for a group."""
    group = session.get(AlgorithmGroup, group_id)
    if not group:
        raise HTTPException(
            status_code=404,
            detail={"detail": "Algorithm group not found", "code": "NOT_FOUND"},
        )

    counts_subquery = (
        select(
            AlgorithmReviewItem.algorithm_id,
            func.count(AlgorithmReviewItem.id).label("review_items_count"),
        )
        .group_by(AlgorithmReviewItem.algorithm_id)
        .subquery()
    )
    rows = session.execute(
        select(
            Algorithm,
            func.coalesce(counts_subquery.c.review_items_count, 0),
        )
        .outerjoin(counts_subquery, counts_subquery.c.algorithm_id == Algorithm.id)
        .where(Algorithm.group_id == group_id)
        .order_by(Algorithm.id)
    ).all()

    return [
        AlgorithmListOut(
            id=algorithm.id,
            group_id=group.id,
            group_title=group.title,
            title=algorithm.title,
            summary=algorithm.summary,
            complexity=algorithm.complexity,
            review_items_count=int(review_items_count or 0),
        )
        for algorithm, review_items_count in rows
    ]


@router.get("/algorithms/{algorithm_id}")
def get_algorithm_detail(
    algorithm_id: int,
    session: Session = Depends(get_session),
) -> AlgorithmDetailOut:
    """Get algorithm detail with code snippets and source part."""
    row = session.execute(
        select(Algorithm, AlgorithmGroup)
        .join(AlgorithmGroup, Algorithm.group_id == AlgorithmGroup.id)
        .where(Algorithm.id == algorithm_id)
        .limit(1)
    ).first()

    if not row:
        raise HTTPException(
            status_code=404,
            detail={"detail": "Algorithm not found", "code": "NOT_FOUND"},
        )

    algorithm, group = row
    code_snippets = (
        session.execute(
            select(AlgorithmCodeSnippet)
            .where(AlgorithmCodeSnippet.algorithm_id == algorithm.id)
            .order_by(AlgorithmCodeSnippet.id)
        )
        .scalars()
        .all()
    )
    source_part = (
        session.get(ReadingPart, algorithm.source_part_id)
        if algorithm.source_part_id
        else None
    )
    source_part_out = (
        ReadingPartOut.model_validate(source_part) if source_part else None
    )
    review_items_count = session.execute(
        select(func.count(AlgorithmReviewItem.id)).where(
            AlgorithmReviewItem.algorithm_id == algorithm.id
        )
    ).scalar_one()

    return AlgorithmDetailOut(
        id=algorithm.id,
        group_id=group.id,
        group_title=group.title,
        title=algorithm.title,
        summary=algorithm.summary,
        when_to_use=algorithm.when_to_use,
        complexity=algorithm.complexity,
        invariants=algorithm.invariants,
        steps=algorithm.steps,
        corner_cases=algorithm.corner_cases,
        source_part=source_part_out,
        code_snippets=[
            AlgorithmCodeSnippetOut(
                id=snippet.id,
                code_kind=snippet.code_kind,
                language=snippet.language,
                code_text=snippet.code_text,
                is_reference=snippet.is_reference,
                created_at=snippet.created_at,
            )
            for snippet in code_snippets
        ],
        review_items_count=int(review_items_count or 0),
    )


@router.post("/algorithms/import", status_code=status.HTTP_201_CREATED)
def import_algorithms(
    payload: AlgorithmImportPayload,
    session: Session = Depends(get_session),
) -> AlgorithmImportResponse:
    """Import algorithms, groups, and schedule review items."""
    required_titles: list[str] = []
    for item in payload.algorithms:
        group_title = (item.group_title or "").strip()
        if not group_title:
            raise HTTPException(
                status_code=422,
                detail={
                    "detail": "group_title is required for each algorithm",
                    "code": "ALGORITHM_IMPORT_INVALID",
                },
            )
        required_titles.append(group_title)

        questions_map = item.review_questions_by_interval.root
        for interval_value in DEFAULT_INTERVALS:
            questions = _get_questions_for_interval(questions_map, interval_value)
            if not questions:
                raise HTTPException(
                    status_code=422,
                    detail={
                        "detail": (
                            "review_questions_by_interval must include non-empty "
                            f"questions for interval {interval_value}"
                        ),
                        "code": "ALGORITHM_IMPORT_INVALID",
                    },
                )

    for group in payload.groups:
        title = group.title.strip()
        if title and title not in required_titles:
            required_titles.append(title)

    normalized_titles = {normalize_group_title(title) for title in required_titles}
    existing_groups = (
        session.execute(
            select(AlgorithmGroup).where(
                AlgorithmGroup.title_norm.in_(normalized_titles)
            )
        )
        .scalars()
        .all()
    )
    groups_by_norm: dict[str, AlgorithmGroup] = {
        group.title_norm: group for group in existing_groups
    }

    groups_created = 0
    for group_payload in payload.groups:
        title = group_payload.title.strip()
        if not title:
            continue
        _, created = get_or_create_group(
            session,
            title,
            description=group_payload.description,
            notes=group_payload.notes,
            cache=groups_by_norm,
        )
        if created:
            groups_created += 1

    for title in required_titles:
        _, created = get_or_create_group(session, title, cache=groups_by_norm)
        if created:
            groups_created += 1

    algorithms_created = 0
    review_items_created = 0
    base_date = date.today()

    for item in payload.algorithms:
        group_title = item.group_title.strip()
        group = groups_by_norm[normalize_group_title(group_title)]
        algorithm = Algorithm(
            group_id=group.id,
            source_part_id=item.source_part_id,
            title=item.title,
            summary=item.summary,
            when_to_use=item.when_to_use,
            complexity=item.complexity,
            invariants=item.invariants,
            steps=item.steps,
            corner_cases=item.corner_cases,
        )
        session.add(algorithm)
        session.flush()
        algorithms_created += 1

        snippet = AlgorithmCodeSnippet(
            algorithm_id=algorithm.id,
            code_kind=item.code.code_kind,
            language=item.code.language,
            code_text=item.code.code_text,
            is_reference=True,
        )
        session.add(snippet)

        questions_map = item.review_questions_by_interval.root
        for interval_value in DEFAULT_INTERVALS:
            questions = _get_questions_for_interval(questions_map, interval_value)
            review_item = AlgorithmReviewItem(
                algorithm_id=algorithm.id,
                interval_days=interval_value,
                due_date=base_date + timedelta(days=interval_value),
                status="planned",
                questions=questions,
            )
            session.add(review_item)
            review_items_created += 1

    session.commit()

    logger.info(
        "Imported algorithms",
        extra={
            "groups_created": groups_created,
            "algorithms_created": algorithms_created,
            "review_items_created": review_items_created,
        },
    )

    return AlgorithmImportResponse(
        groups_created=groups_created,
        algorithms_created=algorithms_created,
        review_items_created=review_items_created,
    )
