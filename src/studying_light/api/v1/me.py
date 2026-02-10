"""Current user endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from studying_light.api.v1.deps import get_current_user, touch_last_seen
from studying_light.api.v1.schemas import StatusOkResponse
from studying_light.db.models.user import User
from studying_light.db.session import get_session

router: APIRouter = APIRouter()


@router.post("/me/heartbeat")
def heartbeat(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> StatusOkResponse:
    """Update last_seen_at with throttle."""
    touch_last_seen(session, current_user)
    return StatusOkResponse()
