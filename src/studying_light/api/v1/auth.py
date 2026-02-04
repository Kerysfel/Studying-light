"""Authentication endpoints."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from studying_light.api.v1.schemas import (
    AuthLogin,
    AuthRegister,
    TokenResponse,
    UserOut,
)
from studying_light.db.models.user import User
from studying_light.db.session import get_session
from studying_light.security import hash_password, verify_password
from studying_light.services.user_settings import build_default_settings

router: APIRouter = APIRouter(prefix="/auth")


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(
    payload: AuthRegister,
    session: Session = Depends(get_session),
) -> UserOut:
    """Register a new user."""
    email = payload.email.strip().lower()
    existing = (
        session.execute(select(User).where(User.email == email))
        .scalar_one_or_none()
    )
    if existing:
        raise HTTPException(
            status_code=409,
            detail={"detail": "Email already exists", "code": "USER_EXISTS"},
        )

    user = User(
        email=email,
        password_hash=hash_password(payload.password),
        is_active=True,
    )
    session.add(user)
    session.flush()

    settings = build_default_settings(user.id)
    session.add(settings)
    session.commit()
    session.refresh(user)
    return UserOut.model_validate(user)


@router.post("/login")
def login(
    payload: AuthLogin,
    session: Session = Depends(get_session),
) -> TokenResponse:
    """Login and return access token."""
    email = payload.email.strip().lower()
    user = (
        session.execute(select(User).where(User.email == email))
        .scalar_one_or_none()
    )
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=401,
            detail={"detail": "Invalid credentials", "code": "UNAUTHORIZED"},
        )
    if not user.is_active:
        raise HTTPException(
            status_code=403,
            detail={"detail": "User is inactive", "code": "USER_INACTIVE"},
        )

    user.last_login_at = datetime.now(timezone.utc)
    session.commit()
    session.refresh(user)
    return TokenResponse(access_token=str(user.id), token_type="bearer")
