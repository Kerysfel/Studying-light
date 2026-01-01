"""Review schedule item model."""

from datetime import datetime, date

from sqlalchemy import Date, DateTime, ForeignKey, Integer, JSON, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from studying_light.db.base import Base


class ReviewScheduleItem(Base):
    """Scheduled review item."""

    __tablename__ = "review_schedule_items"

    id: Mapped[int] = mapped_column(primary_key=True)
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
