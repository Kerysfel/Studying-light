"""Authentication endpoints."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from studying_light.api.v1.deps import get_current_user
from studying_light.api.v1.schemas import (
    AuthLogin,
    AuthMeOut,
    AuthRegister,
    ChangePasswordPayload,
    RequestPasswordResetPayload,
    StatusOkResponse,
    TokenResponse,
    UserOut,
)
from studying_light.db.models.password_reset_request import PasswordResetRequest
from studying_light.db.models.user import User
from studying_light.db.models.user_settings import UserSettings
from studying_light.db.session import get_session
from studying_light.security import (
    create_access_token,
    hash_password,
    is_legacy_sha256_hash,
    verify_password,
)
from studying_light.services.user_settings import build_default_settings

router: APIRouter = APIRouter(prefix="/auth")


def _normalize_datetime(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _can_login_with_temp_password(user: User, now: datetime) -> bool:
    expires_at = _normalize_datetime(user.temp_password_expires_at)
    if user.temp_password_hash is None or expires_at is None:
        return False
    if expires_at < now:
        return False
    return user.temp_password_used_at is None


def _can_use_temp_password_for_change(user: User, now: datetime) -> bool:
    expires_at = _normalize_datetime(user.temp_password_expires_at)
    if user.temp_password_hash is None or expires_at is None:
        return False
    return expires_at >= now


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
        is_active=False,
        is_admin=False,
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
    email = payload.email
    user = (
        session.execute(select(User).where(User.email == email))
        .scalar_one_or_none()
    )
    if not user:
        raise HTTPException(
            status_code=401,
            detail={"detail": "Invalid credentials", "code": "AUTH_INVALID"},
        )

    now = datetime.now(timezone.utc)
    temp_active = _can_login_with_temp_password(user, now)
    temp_password_valid = False
    if temp_active and user.temp_password_hash is not None:
        temp_password_valid = verify_password(payload.password, user.temp_password_hash)
    regular_password_valid = verify_password(payload.password, user.password_hash)

    if not temp_password_valid and not regular_password_valid:
        raise HTTPException(
            status_code=401,
            detail={"detail": "Invalid credentials", "code": "AUTH_INVALID"},
        )
    if not user.is_active:
        raise HTTPException(
            status_code=403,
            detail={"detail": "Account is inactive", "code": "ACCOUNT_INACTIVE"},
        )

    if temp_password_valid:
        user.temp_password_used_at = now
        user.must_change_password = True
    elif is_legacy_sha256_hash(user.password_hash):
        # Opportunistically migrate legacy hashes to Argon2 on successful login.
        user.password_hash = hash_password(payload.password)

    user.last_login_at = now
    session.commit()
    session.refresh(user)
    return TokenResponse(access_token=create_access_token(user.id), token_type="bearer")


@router.get("/me")
def me(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> AuthMeOut:
    """Return current authenticated user profile."""
    settings = session.get(UserSettings, current_user.id)
    return AuthMeOut(
        id=current_user.id,
        email=current_user.email,
        is_active=current_user.is_active,
        is_admin=current_user.is_admin,
        must_change_password=current_user.must_change_password,
        timezone=settings.timezone if settings else None,
    )


@router.post("/request-password-reset")
def request_password_reset(
    payload: RequestPasswordResetPayload,
    session: Session = Depends(get_session),
) -> StatusOkResponse:
    """Create password reset request if email exists, without leaking existence."""
    user = (
        session.execute(select(User).where(User.email == payload.email))
        .scalar_one_or_none()
    )
    if user:
        session.add(
            PasswordResetRequest(
                user_id=user.id,
                status="requested",
            )
        )
        session.commit()
    return StatusOkResponse()


@router.post("/change-password")
def change_password(
    payload: ChangePasswordPayload,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> StatusOkResponse:
    """Change current user password."""
    now = datetime.now(timezone.utc)
    if _can_use_temp_password_for_change(current_user, now):
        current_valid = (
            current_user.temp_password_hash is not None
            and verify_password(
                payload.current_password,
                current_user.temp_password_hash,
            )
        )
    else:
        current_valid = verify_password(
            payload.current_password,
            current_user.password_hash,
        )

    if not current_valid:
        raise HTTPException(
            status_code=401,
            detail={"detail": "Invalid credentials", "code": "AUTH_INVALID"},
        )

    current_user.password_hash = hash_password(payload.new_password)
    current_user.must_change_password = False
    current_user.temp_password_hash = None
    current_user.temp_password_expires_at = None
    current_user.temp_password_used_at = None
    session.commit()
    return StatusOkResponse()
