"""Review attempt model."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, JSON, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from studying_light.db.base import Base


class ReviewAttempt(Base):
    """Review attempt entity."""

    __tablename__ = "review_attempts"

    id: Mapped[int] = mapped_column(primary_key=True)
    review_item_id: Mapped[int] = mapped_column(
        ForeignKey("review_schedule_items.id"),
        index=True,
    )
    answers: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    gpt_check_result: Mapped[str | None] = mapped_column(Text, nullable=True)

    review_item: Mapped["ReviewScheduleItem"] = relationship(back_populates="attempts")
