"""Algorithm code snippet model."""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from studying_light.db.base import Base


class AlgorithmCodeSnippet(Base):
    """Algorithm code snippet entity."""

    __tablename__ = "algorithm_code_snippets"

    id: Mapped[int] = mapped_column(primary_key=True)
    algorithm_id: Mapped[int] = mapped_column(
        ForeignKey("algorithms.id"),
        index=True,
    )
    code_kind: Mapped[str] = mapped_column(String(16))
    language: Mapped[str] = mapped_column(String(32))
    code_text: Mapped[str] = mapped_column(Text)
    is_reference: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    algorithm: Mapped["Algorithm"] = relationship(back_populates="code_snippets")
