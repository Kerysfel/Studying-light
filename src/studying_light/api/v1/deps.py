"""API dependencies."""

from datetime import datetime, timezone

from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from studying_light.db.models.user import User
from studying_light.db.session import get_session
from studying_light.security import TokenValidationError, decode_access_token

LAST_SEEN_THROTTLE_SECONDS = 60


def _parse_bearer_token(authorization: str | None) -> str:
    if not authorization:
        raise HTTPException(
            status_code=401,
            detail={
                "detail": "Authorization header is required",
                "code": "AUTH_REQUIRED",
            },
        )
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail={"detail": "Invalid Authorization header", "code": "AUTH_INVALID"},
        )
    token = authorization.removeprefix("Bearer ").strip()
    if not token:
        raise HTTPException(
            status_code=401,
            detail={"detail": "Invalid access token", "code": "AUTH_INVALID"},
        )
    return token


def _resolve_user_from_token(session: Session, token: str) -> User:
    try:
        user_id = decode_access_token(token)
    except TokenValidationError as exc:
        raise HTTPException(
            status_code=401,
            detail={"detail": "Invalid access token", "code": "AUTH_INVALID"},
        ) from exc

    user = session.get(User, user_id)
    if not user:
        raise HTTPException(
            status_code=401,
            detail={"detail": "Invalid access token", "code": "AUTH_INVALID"},
        )
    if not user.is_active:
        raise HTTPException(
            status_code=403,
            detail={"detail": "Account is inactive", "code": "ACCOUNT_INACTIVE"},
        )
    return user


def touch_last_seen(session: Session, user: User) -> None:
    now = datetime.now(timezone.utc)
    last_seen = user.last_seen_at
    if last_seen is not None and last_seen.tzinfo is None:
        last_seen = last_seen.replace(tzinfo=timezone.utc)
    if last_seen is not None:
        elapsed = (now - last_seen).total_seconds()
        if elapsed < LAST_SEEN_THROTTLE_SECONDS:
            return
    user.last_seen_at = now
    session.commit()
    session.refresh(user)


def get_current_user(
    authorization: str | None = Header(default=None),
    session: Session = Depends(get_session),
) -> User:
    """Return the authenticated user."""
    token = _parse_bearer_token(authorization)
    user = _resolve_user_from_token(session, token)
    touch_last_seen(session, user)
    return user


def get_optional_user(
    authorization: str | None = Header(default=None),
    session: Session = Depends(get_session),
) -> User | None:
    """Return the authenticated user if provided."""
    if not authorization:
        return None
    token = _parse_bearer_token(authorization)
    user = _resolve_user_from_token(session, token)
    touch_last_seen(session, user)
    return user


def get_current_admin_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """Return authenticated admin user."""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=403,
            detail={"detail": "Admin access required", "code": "FORBIDDEN"},
        )
    return current_user
