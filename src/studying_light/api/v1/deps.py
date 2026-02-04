"""API dependencies."""

from datetime import datetime, timezone
from uuid import UUID

from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from studying_light.db.models.user import User
from studying_light.db.session import get_session


def _parse_bearer_token(authorization: str | None) -> UUID:
    if not authorization:
        raise HTTPException(
            status_code=401,
            detail={"detail": "Missing Authorization header", "code": "UNAUTHORIZED"},
        )
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail={"detail": "Invalid Authorization header", "code": "UNAUTHORIZED"},
        )
    token = authorization.removeprefix("Bearer ").strip()
    try:
        return UUID(token)
    except ValueError as exc:
        raise HTTPException(
            status_code=401,
            detail={"detail": "Invalid access token", "code": "UNAUTHORIZED"},
        ) from exc


def get_current_user(
    authorization: str | None = Header(default=None),
    session: Session = Depends(get_session),
) -> User:
    """Return the authenticated user."""
    user_id = _parse_bearer_token(authorization)
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(
            status_code=401,
            detail={"detail": "Invalid access token", "code": "UNAUTHORIZED"},
        )
    if not user.is_active:
        raise HTTPException(
            status_code=403,
            detail={"detail": "User is inactive", "code": "USER_INACTIVE"},
        )
    user.last_seen_at = datetime.now(timezone.utc)
    session.commit()
    session.refresh(user)
    return user


def get_optional_user(
    authorization: str | None = Header(default=None),
    session: Session = Depends(get_session),
) -> User | None:
    """Return the authenticated user if provided."""
    if not authorization:
        return None
    user_id = _parse_bearer_token(authorization)
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(
            status_code=401,
            detail={"detail": "Invalid access token", "code": "UNAUTHORIZED"},
        )
    if not user.is_active:
        raise HTTPException(
            status_code=403,
            detail={"detail": "User is inactive", "code": "USER_INACTIVE"},
        )
    user.last_seen_at = datetime.now(timezone.utc)
    session.commit()
    session.refresh(user)
    return user
