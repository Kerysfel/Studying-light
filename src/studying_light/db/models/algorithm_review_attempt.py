"""Algorithm review attempt model."""

import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from studying_light.db.base import Base


class AlgorithmReviewAttempt(Base):
    """Algorithm review attempt entity."""

    __tablename__ = "algorithm_review_attempts"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id"),
        index=True,
    )
    review_item_id: Mapped[int] = mapped_column(
        ForeignKey("algorithm_review_items.id"),
        index=True,
    )
    answers: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    gpt_check_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    rating_1_to_5: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    review_item: Mapped["AlgorithmReviewItem"] = relationship(back_populates="attempts")
