"""Shared API structures."""

from pydantic import BaseModel, Field, RootModel


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
