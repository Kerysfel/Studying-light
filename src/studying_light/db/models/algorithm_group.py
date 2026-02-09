"""Algorithm group model."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from studying_light.db.base import Base


def normalize_group_title(title: str) -> str:
    """Normalize an algorithm group title for comparisons."""
    return title.strip().lower()


class AlgorithmGroup(Base):
    """Algorithm group entity."""

    __tablename__ = "algorithm_groups"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "title_norm",
            name="uq_algorithm_groups_user_id_title_norm",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id"),
        index=True,
    )
    title: Mapped[str] = mapped_column(String(255))
    title_norm: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    algorithms: Mapped[list["Algorithm"]] = relationship(
        back_populates="group",
        cascade="all, delete-orphan",
    )

    @validates("title")
    def _set_title_norm(self, _key: str, value: str) -> str:
        self.title_norm = normalize_group_title(value)
        return value
