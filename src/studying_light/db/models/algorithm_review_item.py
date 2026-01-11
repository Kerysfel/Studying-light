"""Algorithm review item model."""

from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from studying_light.db.base import Base


class AlgorithmReviewItem(Base):
    """Algorithm scheduled review item."""

    __tablename__ = "algorithm_review_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    algorithm_id: Mapped[int] = mapped_column(
        ForeignKey("algorithms.id"),
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

    algorithm: Mapped["Algorithm"] = relationship(back_populates="review_items")
    attempts: Mapped[list["AlgorithmReviewAttempt"]] = relationship(
        back_populates="review_item",
        cascade="all, delete-orphan",
    )
