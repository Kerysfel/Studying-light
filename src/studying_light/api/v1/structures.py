"""Shared API structures."""

from datetime import date

from pydantic import BaseModel, Field, RootModel, field_validator


class TermItem(BaseModel):
    """Term entry."""

    term: str
    definition: str | None = None


class RawNotes(BaseModel):
    """Raw notes payload."""

    keywords: list[str] = Field(default_factory=list)
    terms: list[TermItem] = Field(default_factory=list)
    sentences: list[str] = Field(default_factory=list)
    freeform: list[str] = Field(default_factory=list)


class GptQuestionsByInterval(RootModel[dict[int, list[str]]]):
    """Questions grouped by interval days."""


class GptReviewMeta(BaseModel):
    """Metadata for GPT review checks."""

    book_title: str
    part_index: int
    part_label: str
    interval_days: int | None = None
    review_date: date


class GptReviewOverall(BaseModel):
    """Overall GPT review evaluation."""

    rating_1_to_5: int
    score_0_to_100: int
    verdict: str
    key_gaps: list[str]
    next_steps: list[str]
    limitations: list[str]

    @field_validator("rating_1_to_5")
    @classmethod
    def validate_rating(cls, value: int) -> int:
        """Ensure rating is between 1 and 5."""
        if value < 1 or value > 5:
            raise ValueError("rating_1_to_5 must be between 1 and 5")
        return value

    @field_validator("score_0_to_100")
    @classmethod
    def validate_score(cls, value: int) -> int:
        """Ensure score is between 0 and 100."""
        if value < 0 or value > 100:
            raise ValueError("score_0_to_100 must be between 0 and 100")
        return value

    @field_validator("verdict")
    @classmethod
    def validate_verdict(cls, value: str) -> str:
        """Ensure verdict is a supported value."""
        if value not in {"PASS", "PARTIAL", "FAIL"}:
            raise ValueError("verdict must be PASS, PARTIAL, or FAIL")
        return value


class GptReviewItem(BaseModel):
    """Per-question GPT review result."""

    question: str
    user_answer: str
    rating_1_to_5: int
    is_answered: bool
    mistakes: list[str]
    short_feedback: str
    correct_answer: str

    @field_validator("rating_1_to_5")
    @classmethod
    def validate_rating(cls, value: int) -> int:
        """Ensure rating is between 1 and 5."""
        if value < 1 or value > 5:
            raise ValueError("rating_1_to_5 must be between 1 and 5")
        return value


class GptReviewResult(BaseModel):
    """GPT review payload."""

    meta: GptReviewMeta
    overall: GptReviewOverall
    items: list[GptReviewItem]

    @field_validator("items")
    @classmethod
    def validate_items(cls, value: list[GptReviewItem]) -> list[GptReviewItem]:
        """Ensure at least one item is provided."""
        if not value:
            raise ValueError("items cannot be empty")
        return value
