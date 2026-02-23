"""Admin endpoints."""

import secrets
import string
import uuid
from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from studying_light.api.v1.deps import get_current_admin_user
from studying_light.api.v1.schemas import (
    AdminIssueTempPasswordOut,
    AdminPasswordResetRequestOut,
    AdminUserActivitiesListOut,
    AdminUserActivityEventOut,
    AdminUserOut,
    AdminUserPerformanceDetailOut,
    AdminUserPerformanceItemOut,
    AdminUsersPerformanceListOut,
)
from studying_light.db.models.password_reset_request import PasswordResetRequest
from studying_light.db.models.user import User
from studying_light.db.session import get_session
from studying_light.security import hash_password
from studying_light.services.admin_performance_service import (
    get_user_identity,
    get_user_performance,
    list_user_activity_events,
    list_users_performance,
)
from studying_light.services.audit_log import record_audit_event

router: APIRouter = APIRouter(prefix="/admin")

ONLINE_WINDOW = timedelta(minutes=10)
TEMP_PASSWORD_MIN_LENGTH = 12
TEMP_PASSWORD_MAX_LENGTH = 16
TEMP_PASSWORD_TTL_HOURS = 24
TEMP_PASSWORD_ALPHABET = string.ascii_letters + string.digits


def _normalize_datetime(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _is_online(last_seen_at: datetime | None, now: datetime) -> bool:
    normalized = _normalize_datetime(last_seen_at)
    if normalized is None:
        return False
    return (now - normalized) < ONLINE_WINDOW


def _build_admin_user_out(user: User, now: datetime) -> AdminUserOut:
    return AdminUserOut(
        id=user.id,
        email=user.email,
        is_active=user.is_active,
        is_admin=user.is_admin,
        created_at=user.created_at,
        last_login_at=user.last_login_at,
        last_seen_at=user.last_seen_at,
        online=_is_online(user.last_seen_at, now),
    )


def _generate_temp_password() -> str:
    length = secrets.randbelow(TEMP_PASSWORD_MAX_LENGTH - TEMP_PASSWORD_MIN_LENGTH + 1)
    target_length = TEMP_PASSWORD_MIN_LENGTH + length
    return "".join(
        secrets.choice(TEMP_PASSWORD_ALPHABET)
        for _ in range(target_length)
    )


def _validation_error(detail: str) -> HTTPException:
    return HTTPException(
        status_code=422,
        detail={
            "detail": detail,
            "code": "VALIDATION_ERROR",
        },
    )


def _ensure_user_exists(
    session: Session,
    *,
    user_id: uuid.UUID,
) -> dict:
    user_info = get_user_identity(session, user_id=user_id)
    if user_info is None:
        raise HTTPException(
            status_code=404,
            detail={"detail": "User not found", "code": "NOT_FOUND"},
        )
    return user_info


@router.get("/users")
def list_users(
    query: str | None = None,
    status: str | None = None,
    session: Session = Depends(get_session),
    current_admin: User = Depends(get_current_admin_user),
) -> list[AdminUserOut]:
    """List users for admin."""
    del current_admin
    stmt = select(User).order_by(User.created_at.desc())
    if query:
        lowered = f"%{query.strip().lower()}%"
        stmt = stmt.where(User.email.ilike(lowered))

    if status:
        status_value = status.strip().lower()
        if status_value not in {"active", "inactive"}:
            raise HTTPException(
                status_code=422,
                detail={
                    "detail": "status must be active or inactive",
                    "code": "VALIDATION_ERROR",
                },
            )
        stmt = stmt.where(User.is_active.is_(status_value == "active"))

    users = session.execute(stmt).scalars().all()
    now = datetime.now(timezone.utc)
    return [_build_admin_user_out(user, now) for user in users]


@router.get("/users/performance")
def list_users_performance_view(
    search: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    limit: int = Query(default=20, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    sort_by: str = "last_activity_at",
    sort_dir: str = "desc",
    session: Session = Depends(get_session),
    current_admin: User = Depends(get_current_admin_user),
) -> AdminUsersPerformanceListOut:
    """List users with aggregated performance metrics."""
    del current_admin
    try:
        items, total = list_users_performance(
            session,
            search=search,
            date_from=date_from,
            date_to=date_to,
            limit=limit,
            offset=offset,
            sort_by=sort_by,
            sort_dir=sort_dir,
        )
    except ValueError as exc:
        raise _validation_error(str(exc)) from exc

    return AdminUsersPerformanceListOut(
        items=[AdminUserPerformanceItemOut(**item) for item in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/users/{user_id}/performance")
def get_user_performance_view(
    user_id: uuid.UUID,
    date_from: date | None = None,
    date_to: date | None = None,
    session: Session = Depends(get_session),
    current_admin: User = Depends(get_current_admin_user),
) -> AdminUserPerformanceDetailOut:
    """Return aggregated performance summary for one user."""
    del current_admin
    user_info = _ensure_user_exists(session, user_id=user_id)
    try:
        summary = get_user_performance(
            session,
            user_id=user_id,
            date_from=date_from,
            date_to=date_to,
        )
    except ValueError as exc:
        raise _validation_error(str(exc)) from exc

    return AdminUserPerformanceDetailOut(
        user_id=user_info["user_id"],
        email=user_info["email"],
        name=user_info["name"],
        date_from=date_from,
        date_to=date_to,
        last_activity_at=summary["last_activity_at"],
        total_activity_count=summary["total_activity_count"],
        reading=summary["reading"],
        review_theory=summary["review_theory"],
        review_algorithm_theory=summary["review_algorithm_theory"],
        training_typing=summary["training_typing"],
        training_memory=summary["training_memory"],
    )


@router.get("/users/{user_id}/activities")
def list_user_activities_view(
    user_id: uuid.UUID,
    activity_kind: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    session: Session = Depends(get_session),
    current_admin: User = Depends(get_current_admin_user),
) -> AdminUserActivitiesListOut:
    """Return raw user activity event timeline for admin."""
    del current_admin
    _ensure_user_exists(session, user_id=user_id)
    try:
        events, total = list_user_activity_events(
            session,
            user_id=user_id,
            activity_kind=activity_kind,
            date_from=date_from,
            date_to=date_to,
            limit=limit,
            offset=offset,
        )
    except ValueError as exc:
        raise _validation_error(str(exc)) from exc

    items = [AdminUserActivityEventOut(**event) for event in events]
    return AdminUserActivitiesListOut(
        items=items,
        total=total,
        limit=limit,
        offset=offset,
    )


def _set_user_active(
    *,
    user_id: uuid.UUID,
    active: bool,
    action: str,
    session: Session,
    current_admin: User,
) -> AdminUserOut:
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(
            status_code=404,
            detail={"detail": "User not found", "code": "NOT_FOUND"},
        )
    user.is_active = active
    record_audit_event(
        session,
        actor_user_id=current_admin.id,
        action=action,
        target_user_id=user.id,
    )
    session.commit()
    session.refresh(user)
    return _build_admin_user_out(user, datetime.now(timezone.utc))


@router.patch("/users/{user_id}/activate")
def activate_user(
    user_id: uuid.UUID,
    session: Session = Depends(get_session),
    current_admin: User = Depends(get_current_admin_user),
) -> AdminUserOut:
    """Activate a user."""
    return _set_user_active(
        user_id=user_id,
        active=True,
        action="USER_ACTIVATED",
        session=session,
        current_admin=current_admin,
    )


@router.patch("/users/{user_id}/deactivate")
def deactivate_user(
    user_id: uuid.UUID,
    session: Session = Depends(get_session),
    current_admin: User = Depends(get_current_admin_user),
) -> AdminUserOut:
    """Deactivate a user."""
    return _set_user_active(
        user_id=user_id,
        active=False,
        action="USER_DEACTIVATED",
        session=session,
        current_admin=current_admin,
    )


@router.get("/password-resets")
def list_password_resets(
    status: str | None = None,
    session: Session = Depends(get_session),
    current_admin: User = Depends(get_current_admin_user),
) -> list[AdminPasswordResetRequestOut]:
    """List password reset requests."""
    del current_admin
    stmt = (
        select(PasswordResetRequest, User.email)
        .join(User, User.id == PasswordResetRequest.user_id)
        .order_by(PasswordResetRequest.requested_at.desc())
    )
    if status:
        status_value = status.strip().lower()
        if status_value not in {"requested", "processed"}:
            raise HTTPException(
                status_code=422,
                detail={
                    "detail": "status must be requested or processed",
                    "code": "VALIDATION_ERROR",
                },
            )
        stmt = stmt.where(PasswordResetRequest.status == status_value)

    rows = session.execute(stmt).all()
    return [
        AdminPasswordResetRequestOut(
            id=item.id,
            user_id=item.user_id,
            email=email,
            status=item.status,
            requested_at=item.requested_at,
            processed_at=item.processed_at,
            processed_by_admin_id=item.processed_by_admin_id,
        )
        for item, email in rows
    ]


@router.post("/password-resets/{request_id}/issue-temp-password")
def issue_temp_password(
    request_id: int,
    session: Session = Depends(get_session),
    current_admin: User = Depends(get_current_admin_user),
) -> AdminIssueTempPasswordOut:
    """Issue one-time temp password for a reset request."""
    reset_request = session.get(PasswordResetRequest, request_id)
    if not reset_request:
        raise HTTPException(
            status_code=404,
            detail={"detail": "Password reset request not found", "code": "NOT_FOUND"},
        )
    if reset_request.status != "requested":
        raise HTTPException(
            status_code=409,
            detail={
                "detail": "Password reset request already processed",
                "code": "RESET_ALREADY_PROCESSED",
            },
        )

    user = session.get(User, reset_request.user_id)
    if not user:
        raise HTTPException(
            status_code=404,
            detail={"detail": "User not found", "code": "NOT_FOUND"},
        )

    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(hours=TEMP_PASSWORD_TTL_HOURS)
    temp_password = _generate_temp_password()

    user.temp_password_hash = hash_password(temp_password)
    user.temp_password_expires_at = expires_at
    user.temp_password_used_at = None
    user.must_change_password = True

    reset_request.status = "processed"
    reset_request.processed_at = now
    reset_request.processed_by_admin_id = current_admin.id

    record_audit_event(
        session,
        actor_user_id=current_admin.id,
        action="PASSWORD_RESET_ISSUED",
        target_user_id=user.id,
        payload_json={
            "request_id": request_id,
            "user_id": str(user.id),
            "expires_at": expires_at.isoformat(),
        },
    )
    session.commit()

    return AdminIssueTempPasswordOut(
        temp_password=temp_password,
        expires_at=expires_at,
    )
