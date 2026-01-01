"""Application entrypoint for Studying Light."""

import logging
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.responses import FileResponse

from studying_light.api.prompts import router as prompts_router
from studying_light.api.v1.router import router as api_v1_router

logger = logging.getLogger(__name__)

app: FastAPI = FastAPI()

STATIC_DIR: Path = Path("/app/static")

app.mount(
    "/assets",
    StaticFiles(directory=STATIC_DIR / "assets", check_dir=False),
    name="assets",
)


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    """Serve the SPA entrypoint."""
    return FileResponse(STATIC_DIR / "index.html")


def _error_payload(
    detail: str,
    code: str,
    errors: list[dict] | None = None,
) -> dict[str, object]:
    """Build a consistent error response payload."""
    payload: dict[str, object] = {"detail": detail, "code": code}
    if errors:
        payload["errors"] = errors
    return payload


def _code_from_status(status_code: int) -> str:
    """Map HTTP status codes to error codes."""
    if status_code == 400:
        return "BAD_REQUEST"
    if status_code == 401:
        return "UNAUTHORIZED"
    if status_code == 403:
        return "FORBIDDEN"
    if status_code == 404:
        return "NOT_FOUND"
    if status_code == 409:
        return "CONFLICT"
    if status_code == 422:
        return "VALIDATION_ERROR"
    if status_code == 500:
        return "INTERNAL_ERROR"
    return f"HTTP_{status_code}"


@app.exception_handler(RequestValidationError)
def handle_validation_error(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    """Return clean validation errors for invalid requests."""
    errors: list[dict] = []
    has_json_error = False
    for error in exc.errors():
        error_type = error.get("type")
        if error_type == "json_invalid":
            has_json_error = True
        errors.append(
            {
                "loc": error.get("loc", []),
                "msg": error.get("msg", "Invalid value"),
                "type": error_type,
            }
        )
    if has_json_error:
        detail = "Invalid JSON body"
        code = "INVALID_JSON_BODY"
    else:
        detail = "Validation error"
        if request.url.path.endswith("/import_gpt"):
            code = "IMPORT_PAYLOAD_INVALID"
        else:
            code = "VALIDATION_ERROR"
    return JSONResponse(
        status_code=422,
        content=_error_payload(detail=detail, code=code, errors=errors),
    )


@app.exception_handler(HTTPException)
def handle_http_exception(request: Request, exc: HTTPException) -> JSONResponse:
    """Return unified error format for HTTP exceptions."""
    detail = exc.detail
    if isinstance(detail, dict):
        payload = dict(detail)
        if "detail" not in payload:
            payload["detail"] = "Request error"
        if "code" not in payload:
            payload["code"] = _code_from_status(exc.status_code)
        return JSONResponse(status_code=exc.status_code, content=payload)

    return JSONResponse(
        status_code=exc.status_code,
        content=_error_payload(
            detail=str(detail),
            code=_code_from_status(exc.status_code),
        ),
    )


@app.exception_handler(Exception)
def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
    """Return a generic error for unexpected failures."""
    logger.exception("Unhandled error", exc_info=exc)
    return JSONResponse(
        status_code=500,
        content=_error_payload(
            detail="Internal server error",
            code="INTERNAL_ERROR",
        ),
    )


@app.get("/health")
def health() -> dict[str, str]:
    """Return application health status."""
    return {"status": "ok"}


app.include_router(api_v1_router)
app.include_router(prompts_router)


@app.get("/{full_path:path}", include_in_schema=False)
def spa_fallback(full_path: str) -> FileResponse:
    """Serve the SPA for non-API routes."""
    if (
        full_path == "api"
        or full_path.startswith("api/")
        or full_path == "prompts"
        or full_path.startswith("prompts/")
    ):
        raise HTTPException(
            status_code=404,
            detail={"detail": "Not Found", "code": "NOT_FOUND"},
        )
    return FileResponse(STATIC_DIR / "index.html")
