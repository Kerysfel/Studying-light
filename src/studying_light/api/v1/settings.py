"""Settings endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from studying_light.api.v1.schemas import SettingsOut
from studying_light.db.models.user_settings import UserSettings
from studying_light.db.session import get_session

router: APIRouter = APIRouter()

DEFAULT_INTERVALS: list[int] = [1, 7, 16, 35, 90]


def _get_or_create_settings(session: Session) -> UserSettings:
    settings = session.get(UserSettings, 1)
    if settings:
        return settings

    settings = UserSettings(
        id=1,
        timezone="Europe/Amsterdam",
        pomodoro_work_min=25,
        pomodoro_break_min=5,
        daily_goal_weekday_min=40,
        daily_goal_weekend_min=60,
        intervals_days=DEFAULT_INTERVALS,
    )
    session.add(settings)
    session.commit()
    session.refresh(settings)
    return settings


@router.get("/settings")
def get_settings(session: Session = Depends(get_session)) -> SettingsOut:
    """Return application settings."""
    settings = _get_or_create_settings(session)
    return SettingsOut.model_validate(settings)
