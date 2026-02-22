"""User activity event model."""

import uuid
from datetime import datetime

from sqlalchemy import (
    JSON,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Uuid,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from studying_light.db.base import Base
from studying_light.db.constants import (
    ACTIVITY_SOURCE_LIVE,
    ACTIVITY_STATUS_COMPLETED,
    USER_ACTIVITY_KINDS,
    USER_ACTIVITY_SOURCES,
    USER_ACTIVITY_STATUSES,
)


def _as_sql_values(values: tuple[str, ...]) -> str:
    return ", ".join(f"'{value}'" for value in values)


class UserActivityEvent(Base):
    """Append-only user activity event for progress and analytics."""

    __tablename__ = "user_activity_events"
    __table_args__ = (
        CheckConstraint(
            f"activity_kind IN ({_as_sql_values(USER_ACTIVITY_KINDS)})",
            name="ck_user_activity_events_activity_kind",
        ),
        CheckConstraint(
            f"status IN ({_as_sql_values(USER_ACTIVITY_STATUSES)})",
            name="ck_user_activity_events_status",
        ),
        CheckConstraint(
            f"source IN ({_as_sql_values(USER_ACTIVITY_SOURCES)})",
            name="ck_user_activity_events_source",
        ),
        CheckConstraint(
            "duration_sec IS NULL OR duration_sec >= 0",
            name="ck_user_activity_events_duration_non_negative",
        ),
        CheckConstraint(
            "rating_1_to_5 IS NULL OR (rating_1_to_5 >= 1 AND rating_1_to_5 <= 5)",
            name="ck_user_activity_events_rating_range",
        ),
        CheckConstraint(
            "score_0_to_100 IS NULL OR (score_0_to_100 >= 0 AND score_0_to_100 <= 100)",
            name="ck_user_activity_events_score_range",
        ),
        CheckConstraint(
            "started_at IS NULL OR ended_at IS NULL OR ended_at >= started_at",
            name="ck_user_activity_events_time_order",
        ),
        Index(
            "idx_user_activity_events_user_id",
            "user_id",
        ),
        Index(
            "idx_user_activity_events_activity_kind",
            "activity_kind",
        ),
        Index(
            "idx_user_activity_events_status",
            "status",
        ),
        Index(
            "idx_user_activity_events_created_at",
            "created_at",
        ),
        Index(
            "idx_user_activity_events_user_kind_created_at",
            "user_id",
            "activity_kind",
            "created_at",
        ),
        Index(
            "idx_user_activity_events_user_created_at",
            "user_id",
            "created_at",
        ),
        Index(
            "uq_user_activity_events_kind_reading_part",
            "activity_kind",
            "reading_part_id",
            unique=True,
            sqlite_where=text("reading_part_id IS NOT NULL"),
            postgresql_where=text("reading_part_id IS NOT NULL"),
        ),
        Index(
            "uq_user_activity_events_kind_review_attempt",
            "activity_kind",
            "review_attempt_id",
            unique=True,
            sqlite_where=text("review_attempt_id IS NOT NULL"),
            postgresql_where=text("review_attempt_id IS NOT NULL"),
        ),
        Index(
            "uq_user_activity_events_kind_algorithm_review_attempt",
            "activity_kind",
            "algorithm_review_attempt_id",
            unique=True,
            sqlite_where=text("algorithm_review_attempt_id IS NOT NULL"),
            postgresql_where=text("algorithm_review_attempt_id IS NOT NULL"),
        ),
        Index(
            "uq_user_activity_events_kind_algorithm_training_attempt",
            "activity_kind",
            "algorithm_training_attempt_id",
            unique=True,
            sqlite_where=text("algorithm_training_attempt_id IS NOT NULL"),
            postgresql_where=text("algorithm_training_attempt_id IS NOT NULL"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id"),
    )
    activity_kind: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(
        String(24),
        default=ACTIVITY_STATUS_COMPLETED,
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    ended_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    duration_sec: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    score_0_to_100: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rating_1_to_5: Mapped[int | None] = mapped_column(Integer, nullable=True)
    result_label: Mapped[str | None] = mapped_column(String(32), nullable=True)
    accuracy: Mapped[float | None] = mapped_column(Float, nullable=True)

    book_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    reading_part_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    review_item_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    algorithm_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    algorithm_review_item_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    algorithm_training_attempt_id: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    review_attempt_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    algorithm_review_attempt_id: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    source: Mapped[str] = mapped_column(
        String(16),
        default=ACTIVITY_SOURCE_LIVE,
    )
    meta_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
