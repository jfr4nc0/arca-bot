"""
System health and status response models.
"""

from datetime import datetime
from typing import Dict

from pydantic import BaseModel, Field


class HealthCheckResponse(BaseModel):
    """Health check response model."""

    status: str = Field("healthy", description="Service health status")
    timestamp: datetime = Field(default_factory=datetime.now)
    version: str = Field("1.0.0", description="API version")
    services: Dict[str, str] = Field(
        default_factory=dict, description="Status of dependent services"
    )

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class RetryResponse(BaseModel):
    """Retry operation response model."""

    message: str = Field(..., description="Summary of retry operation")
    total_found: int = Field(..., description="Total retryable transactions found")
    retry_initiated: int = Field(
        ..., description="Number of retries successfully initiated"
    )
    retry_failed: int = Field(
        ..., description="Number of retries that failed to initiate"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "message": "Processed 5 retryable transactions, 3 retried successfully",
                "total_found": 5,
                "retry_initiated": 3,
                "retry_failed": 2,
            }
        }
