"""User settings model."""

from sqlalchemy import Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from studying_light.db.base import Base


class UserSettings(Base):
    """User settings entity."""

    __tablename__ = "user_settings"

    id: Mapped[int] = mapped_column(primary_key=True, default=1)
    timezone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    pomodoro_work_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    pomodoro_break_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    daily_goal_weekday_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    daily_goal_weekend_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    intervals_days: Mapped[list | None] = mapped_column(JSON, nullable=True)
