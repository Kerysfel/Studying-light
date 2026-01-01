"""API v1 routes."""

from fastapi import APIRouter

from studying_light.api.v1.books import router as books_router
from studying_light.api.v1.dashboard import router as dashboard_router
from studying_light.api.v1.parts import router as parts_router
from studying_light.api.v1.reviews import router as reviews_router

router: APIRouter = APIRouter(prefix="/api/v1")

router.include_router(books_router, tags=["books"])
router.include_router(parts_router, tags=["parts"])
router.include_router(reviews_router, tags=["reviews"])
router.include_router(dashboard_router, tags=["dashboard"])


@router.get("/health")
def api_health() -> dict[str, str]:
    """Return API health status."""
    return {"status": "ok"}
