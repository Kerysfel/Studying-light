"""Algorithm model."""

from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from studying_light.db.base import Base


class Algorithm(Base):
    """Algorithm entity."""

    __tablename__ = "algorithms"

    id: Mapped[int] = mapped_column(primary_key=True)
    group_id: Mapped[int] = mapped_column(
        ForeignKey("algorithm_groups.id"),
        index=True,
    )
    source_part_id: Mapped[int | None] = mapped_column(
        ForeignKey("reading_parts.id"),
        index=True,
        nullable=True,
    )
    title: Mapped[str] = mapped_column(String(255))
    summary: Mapped[str] = mapped_column(Text)
    when_to_use: Mapped[str] = mapped_column(Text)
    complexity: Mapped[str] = mapped_column(String(64))
    invariants: Mapped[list] = mapped_column(JSON)
    steps: Mapped[list] = mapped_column(JSON)
    corner_cases: Mapped[list] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    group: Mapped["AlgorithmGroup"] = relationship(back_populates="algorithms")
    source_part: Mapped["ReadingPart"] = relationship()
    code_snippets: Mapped[list["AlgorithmCodeSnippet"]] = relationship(
        back_populates="algorithm",
        cascade="all, delete-orphan",
    )
    review_items: Mapped[list["AlgorithmReviewItem"]] = relationship(
        back_populates="algorithm",
        cascade="all, delete-orphan",
    )
