"""User settings model."""

import uuid

from sqlalchemy import JSON, ForeignKey, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from studying_light.db.base import Base


class UserSettings(Base):
    """User settings entity."""

    __tablename__ = "user_settings"

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    timezone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    pomodoro_work_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    pomodoro_break_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    daily_goal_weekday_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    daily_goal_weekend_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    intervals_days: Mapped[list | None] = mapped_column(JSON, nullable=True)

    user: Mapped["User"] = relationship(back_populates="settings")
