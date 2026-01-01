"""Reading part model."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from studying_light.db.base import Base


class ReadingPart(Base):
    """Reading part entity."""

    __tablename__ = "reading_parts"

    id: Mapped[int] = mapped_column(primary_key=True)
    book_id: Mapped[int] = mapped_column(ForeignKey("books.id"), index=True)
    part_index: Mapped[int] = mapped_column(Integer)
    label: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    raw_notes: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    gpt_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    gpt_questions_by_interval: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    book: Mapped["Book"] = relationship(back_populates="reading_parts")
    review_items: Mapped[list["ReviewScheduleItem"]] = relationship(
        back_populates="reading_part",
        cascade="all, delete-orphan",
    )
