"""API v1 routes."""

from fastapi import APIRouter

from studying_light.api.v1.algorithm_reviews import router as algorithm_reviews_router
from studying_light.api.v1.algorithms import router as algorithms_router
from studying_light.api.v1.algorithm_groups import router as algorithm_groups_router
from studying_light.api.v1.books import router as books_router
from studying_light.api.v1.dashboard import router as dashboard_router
from studying_light.api.v1.export import router as export_router
from studying_light.api.v1.parts import router as parts_router
from studying_light.api.v1.reviews import router as reviews_router
from studying_light.api.v1.settings import router as settings_router

router: APIRouter = APIRouter(prefix="/api/v1")

router.include_router(books_router, tags=["books"])
router.include_router(parts_router, tags=["parts"])
router.include_router(reviews_router, tags=["reviews"])
router.include_router(algorithms_router, tags=["algorithms"])
router.include_router(algorithm_groups_router, tags=["algorithm-groups"])
router.include_router(algorithm_reviews_router, tags=["algorithm-reviews"])
router.include_router(dashboard_router, tags=["dashboard"])
router.include_router(settings_router, tags=["settings"])
router.include_router(export_router, tags=["export"])


@router.get("/health")
def api_health() -> dict[str, str]:
    """Return API health status."""
    return {"status": "ok"}
