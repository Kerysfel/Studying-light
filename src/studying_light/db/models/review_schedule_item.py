"""Review schedule item model."""

import uuid
from datetime import date, datetime

from sqlalchemy import JSON, Date, DateTime, ForeignKey, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from studying_light.db.base import Base


class ReviewScheduleItem(Base):
    """Scheduled review item."""

    __tablename__ = "review_schedule_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id"),
        index=True,
    )
    reading_part_id: Mapped[int] = mapped_column(
        ForeignKey("reading_parts.id"),
        index=True,
    )
    interval_days: Mapped[int] = mapped_column(Integer)
    due_date: Mapped[date] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(20), default="planned")
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    questions: Mapped[list | None] = mapped_column(JSON, nullable=True)

    reading_part: Mapped["ReadingPart"] = relationship(back_populates="review_items")
    attempts: Mapped[list["ReviewAttempt"]] = relationship(
        back_populates="review_item",
        cascade="all, delete-orphan",
    )
