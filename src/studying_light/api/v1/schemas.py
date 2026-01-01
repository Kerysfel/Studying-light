"""API schemas."""

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, field_validator

from studying_light.api.v1.structures import GptQuestionsByInterval, RawNotes


class BookCreate(BaseModel):
    """Book creation payload."""

    title: str
    author: str | None = None


class BookUpdate(BaseModel):
    """Book update payload."""

    title: str | None = None
    author: str | None = None
    status: str | None = None


class BookOut(BaseModel):
    """Book response."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    author: str | None = None
    status: str


class ReadingPartCreate(BaseModel):
    """Reading part creation payload."""

    book_id: int
    part_index: int | None = None
    label: str | None = None
    raw_notes: RawNotes | None = None


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


class ReviewCompletePayload(BaseModel):
    """Review completion payload."""

    answers: dict


class ReviewFeedbackPayload(BaseModel):
    """Review feedback payload."""

    gpt_check_result: str


class ReviewAttemptOut(BaseModel):
    """Review attempt response."""

    id: int
    review_item_id: int
    created_at: datetime
    gpt_check_result: str | None = None


class ImportGptResponse(BaseModel):
    """GPT import response."""

    reading_part: ReadingPartOut
    review_items: list[ReviewItemOut]


class TodayResponse(BaseModel):
    """Dashboard response for today."""

    active_books: list[BookOut]
    review_items: list[ReviewItemOut]
