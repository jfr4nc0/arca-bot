"""
Error response models.
"""

from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    """Standard error response model."""

    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Human-readable error message")
    details: Optional[Dict[str, Any]] = Field(
        None, description="Additional error details"
    )
    timestamp: datetime = Field(default_factory=datetime.now)

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}
        json_schema_extra = {
            "example": {
                "error": "ValidationError",
                "message": "Invalid CUIT format provided",
                "details": {"field": "cuit", "expected_format": "11 digits"},
                "timestamp": "2025-01-15T10:30:00",
            }
        }


# DuplicateTransactionResponse removed - using exceptions instead
