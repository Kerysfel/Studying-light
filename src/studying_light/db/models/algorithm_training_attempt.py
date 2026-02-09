"""Algorithm training attempt model."""

import uuid
from datetime import datetime

from sqlalchemy import (
    JSON,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from studying_light.db.base import Base


class AlgorithmTrainingAttempt(Base):
    """Algorithm training attempt entity."""

    __tablename__ = "algorithm_training_attempts"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id"),
        index=True,
    )
    algorithm_id: Mapped[int] = mapped_column(
        ForeignKey("algorithms.id"),
        index=True,
    )
    mode: Mapped[str] = mapped_column(String(16), default="memory")
    code_text: Mapped[str] = mapped_column(Text)
    gpt_check_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    rating_1_to_5: Mapped[int | None] = mapped_column(Integer, nullable=True)
    accuracy: Mapped[float | None] = mapped_column(Float, nullable=True)
    duration_sec: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    algorithm: Mapped["Algorithm"] = relationship(back_populates="training_attempts")
