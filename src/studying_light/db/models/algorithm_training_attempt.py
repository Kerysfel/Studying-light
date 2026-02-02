"""Algorithm training attempt model."""

from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from studying_light.db.base import Base


class AlgorithmTrainingAttempt(Base):
    """Algorithm training attempt entity."""

    __tablename__ = "algorithm_training_attempts"

    id: Mapped[int] = mapped_column(primary_key=True)
    algorithm_id: Mapped[int] = mapped_column(
        ForeignKey("algorithms.id"),
        index=True,
    )
    code_text: Mapped[str] = mapped_column(Text)
    gpt_check_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    rating_1_to_5: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    algorithm: Mapped["Algorithm"] = relationship(back_populates="training_attempts")
