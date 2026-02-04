"""API schemas."""

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from studying_light.api.v1.structures import (
    AlgorithmGptReviewResult,
    AlgorithmGroupPayload,
    AlgorithmImportItem,
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


class UserCreate(BaseModel):
    """User creation payload."""

    email: str
    password: str


class UserOut(BaseModel):
    """User response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    is_active: bool
    is_admin: bool
    created_at: datetime
    last_login_at: datetime | None = None
    last_seen_at: datetime | None = None
    must_change_password: bool


class AuthRegister(BaseModel):
    """Auth registration payload."""

    email: str
    password: str


class AuthLogin(BaseModel):
    """Auth login payload."""

    email: str
    password: str


class TokenResponse(BaseModel):
    """Auth token response."""

    access_token: str
    token_type: str


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
    gpt_rating_1_to_5: int | None = None


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


class ReviewStatsSummaryOut(BaseModel):
    """Summary review stats for a time window."""

    average_rating_7d: float | None = None
    average_rating_30d: float | None = None
    planned_count: int
    completed_count: int


class StatsOverviewOut(BaseModel):
    """Overview stats for theory and algorithm reviews."""

    theory: ReviewStatsSummaryOut
    algorithms: ReviewStatsSummaryOut


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


class AlgorithmReviewCompletePayload(BaseModel):
    """Algorithm review completion payload."""

    answers: dict


class AlgorithmReviewFeedbackPayload(BaseModel):
    """Algorithm review feedback payload."""

    gpt_check_result: AlgorithmGptReviewResult


class AlgorithmReviewAttemptOut(BaseModel):
    """Algorithm review attempt response."""

    id: int
    review_item_id: int
    created_at: datetime
    gpt_check_json: dict | None = None
    rating_1_to_5: int | None = None


class ImportGptResponse(BaseModel):
    """GPT import response."""

    reading_part: ReadingPartOut
    review_items: list[ReviewItemOut]


class AlgorithmImportPayload(BaseModel):
    """Algorithm import payload."""

    groups: list[AlgorithmGroupPayload] = Field(default_factory=list)
    algorithms: list[AlgorithmImportItem]

    @field_validator("algorithms")
    @classmethod
    def validate_algorithms(
        cls,
        value: list[AlgorithmImportItem],
    ) -> list[AlgorithmImportItem]:
        """Ensure algorithms list is not empty."""
        if not value:
            raise ValueError("algorithms cannot be empty")
        return value


class AlgorithmImportResult(BaseModel):
    """Algorithm import creation result."""

    algorithm_id: int
    group_id: int


class AlgorithmImportResponse(BaseModel):
    """Algorithm import response."""

    groups_created: int
    algorithms_created: list[AlgorithmImportResult]
    review_items_created: int


class AlgorithmTrainingCreate(BaseModel):
    """Algorithm training attempt payload."""

    algorithm_id: int
    mode: str = "memory"
    code_text: str
    accuracy: float | None = None
    duration_sec: int | None = None
    gpt_check_result: AlgorithmGptReviewResult | None = None

    @field_validator("algorithm_id")
    @classmethod
    def validate_algorithm_id(cls, value: int) -> int:
        """Ensure algorithm_id is positive."""
        if value <= 0:
            raise ValueError("algorithm_id must be positive")
        return value

    @field_validator("code_text")
    @classmethod
    def validate_code_text(cls, value: str) -> str:
        """Ensure code text is not empty."""
        if not value.strip():
            raise ValueError("code_text cannot be empty")
        return value

    @field_validator("mode")
    @classmethod
    def validate_mode(cls, value: str) -> str:
        """Ensure mode is supported."""
        if value not in {"memory", "typing"}:
            raise ValueError("mode must be memory or typing")
        return value

    @field_validator("accuracy")
    @classmethod
    def validate_accuracy(cls, value: float | None) -> float | None:
        """Ensure accuracy is within 0..100 when provided."""
        if value is None:
            return value
        if value < 0 or value > 100:
            raise ValueError("accuracy must be between 0 and 100")
        return value

    @field_validator("duration_sec")
    @classmethod
    def validate_duration(cls, value: int | None) -> int | None:
        """Ensure duration is positive when provided."""
        if value is None:
            return value
        if value <= 0:
            raise ValueError("duration_sec must be positive")
        return value

    @model_validator(mode="after")
    def validate_mode_requirements(self) -> "AlgorithmTrainingCreate":
        """Ensure mode-specific fields are provided."""
        if self.mode == "typing":
            if self.accuracy is None or self.duration_sec is None:
                raise ValueError("accuracy and duration_sec are required for typing")
        return self


class AlgorithmTrainingAttemptOut(BaseModel):
    """Algorithm training attempt response."""

    id: int
    algorithm_id: int
    mode: str
    code_text: str
    gpt_check_json: dict | None = None
    rating_1_to_5: int | None = None
    accuracy: float | None = None
    duration_sec: int | None = None
    created_at: datetime


class AlgorithmGroupCreate(BaseModel):
    """Algorithm group creation payload."""

    title: str
    description: str | None = None
    notes: str | None = None

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: str) -> str:
        """Ensure group title is not empty."""
        value = value.strip()
        if not value:
            raise ValueError("group title cannot be empty")
        return value


class AlgorithmGroupUpdate(BaseModel):
    """Algorithm group update payload."""

    title: str | None = None
    description: str | None = None
    notes: str | None = None

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: str | None) -> str | None:
        """Ensure group title is not empty when provided."""
        if value is None:
            return value
        value = value.strip()
        if not value:
            raise ValueError("group title cannot be empty")
        return value


class AlgorithmGroupListOut(BaseModel):
    """Algorithm group list response."""

    id: int
    title: str
    description: str | None = None
    notes: str | None = None
    algorithms_count: int


class AlgorithmGroupAlgorithmOut(BaseModel):
    """Algorithm summary for group detail response."""

    id: int
    title: str
    summary: str
    complexity: str


class AlgorithmGroupDetailOut(BaseModel):
    """Algorithm group detail response."""

    id: int
    title: str
    description: str | None = None
    notes: str | None = None
    algorithms_count: int
    algorithms: list[AlgorithmGroupAlgorithmOut]


class AlgorithmGroupMergePayload(BaseModel):
    """Algorithm group merge payload."""

    target_group_id: int

    @field_validator("target_group_id")
    @classmethod
    def validate_target_group_id(cls, value: int) -> int:
        """Ensure target group id is positive."""
        if value <= 0:
            raise ValueError("target_group_id must be positive")
        return value


class AlgorithmCodeSnippetOut(BaseModel):
    """Algorithm code snippet response."""

    id: int
    code_kind: str
    language: str
    code_text: str
    is_reference: bool
    created_at: datetime


class AlgorithmListOut(BaseModel):
    """Algorithm list response."""

    id: int
    group_id: int
    group_title: str
    title: str
    summary: str
    complexity: str
    review_items_count: int


class AlgorithmDetailOut(BaseModel):
    """Algorithm detail response."""

    id: int
    group_id: int
    group_title: str
    title: str
    summary: str
    when_to_use: str
    complexity: str
    invariants: list[str]
    steps: list[str]
    corner_cases: list[str]
    source_part: ReadingPartOut | None = None
    code_snippets: list[AlgorithmCodeSnippetOut]
    review_items_count: int


class AlgorithmReviewItemOut(BaseModel):
    """Algorithm review item response."""

    id: int
    algorithm_id: int
    interval_days: int
    due_date: date
    status: str
    group_id: int
    group_title: str
    title: str
    gpt_rating_1_to_5: int | None = None


class AlgorithmReviewDetailOut(BaseModel):
    """Algorithm review detail response."""

    id: int
    algorithm_id: int
    interval_days: int
    due_date: date
    status: str
    group_id: int
    group_title: str
    title: str
    summary: str
    when_to_use: str
    complexity: str
    invariants: list[str]
    steps: list[str]
    corner_cases: list[str]
    questions: list[str]
    gpt_feedback: AlgorithmGptReviewResult | None = None


class TodayResponse(BaseModel):
    """Dashboard response for today."""

    active_books: list[BookProgressOut]
    review_items: list[ReviewItemOut]
    overdue_review_items: list[ReviewItemOut]
    algorithm_review_items: list[AlgorithmReviewItemOut]
    review_progress: ReviewProgressOut


class AlgorithmReviewStatsOut(BaseModel):
    """Algorithm review statistics."""

    group_id: int
    group_title: str
    algorithm_id: int
    algorithm_title: str
    total_reviews: int
    completed_reviews: int
    gpt_attempts_total: int
    gpt_average_rating: float | None = None


class SettingsOut(BaseModel):
    """Settings response."""

    model_config = ConfigDict(from_attributes=True)

    user_id: UUID
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
