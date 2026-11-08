from fastapi import APIRouter
from ..core.config import settings
from ..services.model_service import model_service
from ..schemas.prediction import HealthResponse

router = APIRouter(prefix="/api", tags=["System Health"])

@router.get(
    "/health",
    response_model=HealthResponse,
    summary="System and Model Health Status",
    description="Reports the operational status of the VisionCare API and the availability of the VGG19 screening model."
)
async def check_health() -> HealthResponse:
    """
    Returns API operational metrics and honest model configuration status.
    If the model artifact is absent, available will be reported as false.
    """
    model_status = model_service.get_status()

    return HealthResponse(
        status="healthy",
        app_name=settings.PROJECT_NAME,
        version=settings.PROJECT_VERSION,
        model=model_status
    )

