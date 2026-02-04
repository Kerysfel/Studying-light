"""Settings endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from studying_light.api.v1.schemas import SettingsOut, SettingsUpdate
from studying_light.api.v1.deps import get_current_user
from studying_light.db.models.user import User
from studying_light.db.models.user_settings import UserSettings
from studying_light.db.session import get_session
from studying_light.services.user_settings import build_default_settings

router: APIRouter = APIRouter()

def _get_or_create_settings(session: Session, user: User) -> UserSettings:
    settings = session.get(UserSettings, user.id)
    if settings:
        return settings

    settings = build_default_settings(user.id)
    session.add(settings)
    session.commit()
    session.refresh(settings)
    return settings


@router.get("/settings")
def get_settings(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> SettingsOut:
    """Return application settings."""
    settings = _get_or_create_settings(session, current_user)
    return SettingsOut.model_validate(settings)


@router.patch("/settings")
def update_settings(
    payload: SettingsUpdate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> SettingsOut:
    """Update application settings."""
    settings = _get_or_create_settings(session, current_user)
    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(
            status_code=400,
            detail={"detail": "No fields provided for update", "code": "BAD_REQUEST"},
        )

    for key, value in updates.items():
        setattr(settings, key, value)

    session.commit()
    session.refresh(settings)
    return SettingsOut.model_validate(settings)
