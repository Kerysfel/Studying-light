"""User settings defaults and helpers."""

import uuid

from studying_light.db.models.user_settings import UserSettings

DEFAULT_SETTINGS = {
    "timezone": "Europe/Amsterdam",
    "pomodoro_work_min": 25,
    "pomodoro_break_min": 5,
    "daily_goal_weekday_min": 40,
    "daily_goal_weekend_min": 60,
    "intervals_days": [1, 7, 16, 35, 90],
}


def build_default_settings(user_id: uuid.UUID) -> UserSettings:
    """Build default settings for a user."""
    return UserSettings(user_id=user_id, **DEFAULT_SETTINGS)
