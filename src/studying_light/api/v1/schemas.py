"""API schemas."""

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, field_validator

from studying_light.api.v1.structures import (
    GptQuestionsByInterval,
    GptReviewResult,
    RawNotes,
)


class BookCreate(BaseModel):
    """Book creation payload."""

    title: str
    author: str | None = None
    pages_total: int | None = None

    @field_validator("pages_total")
    @classmethod
    def validate_pages_total(cls, value: int | None) -> int | None:
        """Ensure pages_total is positive when provided."""
        if value is None:
            return value
        if value <= 0:
            raise ValueError("pages_total must be positive")
        return value


class BookUpdate(BaseModel):
    """Book update payload."""

    title: str | None = None
    author: str | None = None
    status: str | None = None
    pages_total: int | None = None

    @field_validator("pages_total")
    @classmethod
    def validate_pages_total(cls, value: int | None) -> int | None:
        """Ensure pages_total is positive when provided."""
        if value is None:
            return value
        if value <= 0:
            raise ValueError("pages_total must be positive")
        return value


class BookOut(BaseModel):
    """Book response."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    author: str | None = None
    status: str
    pages_total: int | None = None


class BookStatsOut(BaseModel):
    """Book response with reading statistics."""

    id: int
    title: str
    author: str | None = None
    status: str
    pages_total: int | None = None
    pages_read_total: int
    parts_total: int
    sessions_total: int
    reading_seconds_total: int


class ReadingPartCreate(BaseModel):
    """Reading part creation payload."""

    book_id: int
    part_index: int | None = None
    label: str | None = None
    raw_notes: RawNotes | None = None
    pages_read: int | None = None
    session_seconds: int | None = None
    page_end: int | None = None

    @field_validator("pages_read")
    @classmethod
    def validate_pages_read(cls, value: int | None) -> int | None:
        """Ensure pages_read is not negative when provided."""
        if value is None:
            return value
        if value < 0:
            raise ValueError("pages_read must be zero or positive")
        return value

    @field_validator("session_seconds")
    @classmethod
    def validate_session_seconds(cls, value: int | None) -> int | None:
        """Ensure session seconds are not negative when provided."""
        if value is None:
            return value
        if value < 0:
            raise ValueError("session_seconds must be zero or positive")
        return value

    @field_validator("page_end")
    @classmethod
    def validate_page_end(cls, value: int | None) -> int | None:
        """Ensure page_end is positive when provided."""
        if value is None:
            return value
        if value <= 0:
            raise ValueError("page_end must be positive")
        return value


class ReadingPartOut(BaseModel):
    """Reading part response."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    book_id: int
    part_index: int
    label: str | None = None
    created_at: datetime
    raw_notes: dict | None = None
    gpt_summary: str | None = None
    gpt_questions_by_interval: dict | None = None
    pages_read: int | None = None
    session_seconds: int | None = None
    page_end: int | None = None


class ImportGptPayload(BaseModel):
    """GPT import payload."""

    gpt_summary: str
    gpt_questions_by_interval: GptQuestionsByInterval

    @field_validator("gpt_summary")
    @classmethod
    def validate_summary(cls, value: str) -> str:
        """Ensure summary is not empty."""
        if not value.strip():
            raise ValueError("gpt_summary cannot be empty")
        return value

    @field_validator("gpt_questions_by_interval")
    @classmethod
    def validate_intervals(
        cls,
        value: GptQuestionsByInterval,
    ) -> GptQuestionsByInterval:
        """Ensure questions are provided for at least one interval."""
        if not value.root:
            raise ValueError("gpt_questions_by_interval cannot be empty")
        return value


class ReviewItemOut(BaseModel):
    """Review item response."""

    id: int
    reading_part_id: int
    interval_days: int
    due_date: date
    status: str
    book_id: int
    book_title: str
    part_index: int
    label: str | None = None


class ReviewDetailOut(BaseModel):
    """Review detail response."""

    id: int
    reading_part_id: int
    interval_days: int
    due_date: date
    status: str
    book_id: int
    book_title: str
    part_index: int
    label: str | None = None
    summary: str | None = None
    raw_notes: RawNotes | None = None
    questions: list[str]
    gpt_feedback: GptReviewResult | None = None


class ReviewScheduleItemOut(BaseModel):
    """Review schedule item response."""

    id: int
    reading_part_id: int
    interval_days: int
    due_date: date
    status: str


class ReviewScheduleUpdatePayload(BaseModel):
    """Review schedule update payload."""

    due_date: date


class ReviewPartStatsOut(BaseModel):
    """Review statistics per reading part."""

    reading_part_id: int
    book_id: int
    book_title: str
    part_index: int
    label: str | None = None
    summary: str | None = None
    total_reviews: int
    completed_reviews: int
    gpt_attempts_total: int
    gpt_average_rating: float | None = None


class BookProgressOut(BaseModel):
    """Book progress for dashboard."""

    id: int
    title: str
    author: str | None = None
    status: str
    pages_total: int | None = None
    pages_read_total: int


class ReviewProgressOut(BaseModel):
    """Overall review progress."""

    total: int
    completed: int


class ReviewCompletePayload(BaseModel):
    """Review completion payload."""

    answers: dict


class ReviewFeedbackPayload(BaseModel):
    """Review feedback payload."""

    gpt_check_result: GptReviewResult


class ReviewAttemptOut(BaseModel):
    """Review attempt response."""

    id: int
    review_item_id: int
    created_at: datetime
    gpt_check_result: str | None = None
    gpt_check_payload: GptReviewResult | None = None
    gpt_rating_1_to_5: int | None = None
    gpt_score_0_to_100: int | None = None
    gpt_verdict: str | None = None


class ImportGptResponse(BaseModel):
    """GPT import response."""

    reading_part: ReadingPartOut
    review_items: list[ReviewItemOut]


class TodayResponse(BaseModel):
    """Dashboard response for today."""

    active_books: list[BookProgressOut]
    review_items: list[ReviewItemOut]
    review_progress: ReviewProgressOut


class SettingsOut(BaseModel):
    """Settings response."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    timezone: str | None = None
    pomodoro_work_min: int | None = None
    pomodoro_break_min: int | None = None
    daily_goal_weekday_min: int | None = None
    daily_goal_weekend_min: int | None = None
    intervals_days: list | None = None


class SettingsUpdate(BaseModel):
    """Settings update payload."""

    timezone: str | None = None
    pomodoro_work_min: int | None = None
    pomodoro_break_min: int | None = None
    daily_goal_weekday_min: int | None = None
    daily_goal_weekend_min: int | None = None
    intervals_days: list[int] | None = None

    @field_validator("pomodoro_work_min", "pomodoro_break_min")
    @classmethod
    def validate_pomodoro(cls, value: int | None) -> int | None:
        """Ensure pomodoro minutes are positive when provided."""
        if value is None:
            return value
        if value <= 0:
            raise ValueError("pomodoro minutes must be positive")
        return value

    @field_validator("daily_goal_weekday_min", "daily_goal_weekend_min")
    @classmethod
    def validate_goals(cls, value: int | None) -> int | None:
        """Ensure daily goals are positive when provided."""
        if value is None:
            return value
        if value <= 0:
            raise ValueError("daily goal minutes must be positive")
        return value

    @field_validator("intervals_days")
    @classmethod
    def validate_intervals(cls, value: list[int] | None) -> list[int] | None:
        """Ensure intervals are positive when provided."""
        if value is None:
            return value
        if not value:
            raise ValueError("intervals_days cannot be empty")
        if any(interval <= 0 for interval in value):
            raise ValueError("intervals_days must be positive")
        return value

