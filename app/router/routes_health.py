from fastapi import APIRouter

from app.dto.health import HealthResponse
from app.utils.time import utcnow

router = APIRouter()


@router.get("/", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    return HealthResponse(status="HEALTHY", current_time=utcnow())
