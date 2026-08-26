from fastapi import APIRouter, Request

from app.contracts.api import HealthResponse
from app.core.config import Settings

router = APIRouter(tags=["system"])


@router.get("/health", response_model=HealthResponse)
async def health(request: Request) -> HealthResponse:
    """Report whether the HTTP service is available."""
    settings: Settings = request.app.state.settings
    return HealthResponse(
        status="ok",
        service=settings.app_name,
        version=settings.app_version,
        environment=settings.environment,
    )

