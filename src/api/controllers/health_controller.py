"""
Health check controller following Single Responsibility Principle.
"""

from fastapi import APIRouter

from api.models.responses import HealthCheckResponse

router = APIRouter(prefix="/health", tags=["health"])


@router.get(
    "",
    response_model=HealthCheckResponse,
    summary="Health check",
    description="Simple health check",
)
def health_check():
    """Simple health check endpoint."""
    return HealthCheckResponse(services={"api": "healthy"})
