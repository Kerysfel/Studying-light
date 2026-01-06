"""Book model."""

from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from studying_light.db.base import Base


class Book(Base):
    """Book entity."""

    __tablename__ = "books"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(255))
    author: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="active")
    pages_total: Mapped[int | None] = mapped_column(Integer, nullable=True)

    reading_parts: Mapped[list["ReadingPart"]] = relationship(
        back_populates="book",
        cascade="all, delete-orphan",
    )
