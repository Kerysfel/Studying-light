"""Prompt template endpoints."""

from importlib import resources

from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse

router: APIRouter = APIRouter()

ALLOWED_PROMPTS: set[str] = {
    "generate_summary_and_questions",
    "check_answers",
    "generate_algorithms_from_code",
}


@router.get("/prompts/{name}", response_class=PlainTextResponse)
def get_prompt(name: str) -> str:
    """Return a prompt template by name."""
    if name not in ALLOWED_PROMPTS:
        raise HTTPException(
            status_code=404,
            detail={"detail": "Prompt not found", "code": "NOT_FOUND"},
        )

    package = resources.files("studying_light.prompts")
    file_path = package.joinpath(f"{name}.txt")
    if not file_path.is_file():
        raise HTTPException(
            status_code=404,
            detail={"detail": "Prompt not found", "code": "NOT_FOUND"},
        )
    return file_path.read_text(encoding="utf-8")
