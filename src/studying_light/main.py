"""Application entrypoint for Studying Light."""

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from starlette.responses import FileResponse

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


@app.get("/{full_path:path}", include_in_schema=False)
def spa_fallback(full_path: str) -> FileResponse:
    """Serve the SPA for non-API routes."""
    if full_path == "api" or full_path.startswith("api/"):
        raise HTTPException(status_code=404, detail="Not Found")
    return FileResponse(STATIC_DIR / "index.html")
