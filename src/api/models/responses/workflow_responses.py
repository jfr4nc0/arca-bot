"""
Workflow execution response models.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from api.models.responses.file_data import FileData


class WorkflowExecutionResponse(BaseModel):
    """Standard response for workflow execution requests."""

    exchange_id: UUID = Field(
        ..., description="Unique identifier for tracking the workflow execution"
    )
    transaction_hash: str = Field(..., description="Hash for duplicate detection")
    status: str = Field("accepted", description="Initial status of the request")
    message: str = Field(
        "Workflow execution started", description="Human-readable status message"
    )
    created_at: datetime = Field(
        default_factory=datetime.now,
        description="Timestamp when the request was created",
    )

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat(), UUID: lambda v: str(v)}
        json_schema_extra = {
            "example": {
                "exchange_id": "550e8400-e29b-41d4-a716-446655440000",
                "transaction_hash": "a1b2c3d4e5f6789012345678901234567890abcdef1234567890abcdef123456",
                "status": "accepted",
                "message": "Workflow execution started",
                "created_at": "2025-01-15T10:30:00",
            }
        }


class WorkflowStatusResponse(BaseModel):
    """Response model for workflow status queries."""

    exchange_id: UUID
    status: str = Field(..., description="Current workflow status")
    started_at: Optional[datetime] = Field(
        None, description="When the workflow started"
    )
    completed_at: Optional[datetime] = Field(
        None, description="When the workflow completed"
    )
    results: Optional[Dict[str, Any]] = Field(
        None, description="Workflow results if completed"
    )
    errors: Optional[Dict[str, Any]] = Field(
        None, description="Error details if failed"
    )

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat(), UUID: lambda v: str(v)}


class VEPGenerationResponse(BaseModel):
    """Specific response for VEP generation workflow."""

    exchange_id: UUID
    vep_transaction_hash: str = Field(..., description="VEP-specific transaction hash")
    status: str
    pdf: Optional[FileData] = Field(None, description="Generated PDF as base64")
    png: Optional[FileData] = Field(None, description="Generated QR/PNG as base64")
    payment_url: Optional[str] = Field(None, description="Payment URL if applicable")

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat(), UUID: lambda v: str(v)}
        json_schema_extra = {
            "example": {
                "exchange_id": "550e8400-e29b-41d4-a716-446655440000",
                "vep_transaction_hash": "a1b2c3d4e5f6789012345678901234567890abcdef1234567890abcdef123456",
                "status": "completed",
                "pdf": {
                    "filename": "vep_20250115_123456.pdf",
                    "content_type": "application/pdf",
                    "data": "JVBERi0xLjQKJeLjz9MKMSAwIG9iago8PAovVHlwZSAvQ2F0YWxvZwov...",
                },
                "png": {
                    "filename": "qr_20250115_123456.png",
                    "content_type": "image/png",
                    "data": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8...",
                },
                "payment_url": "https://payment.afip.gob.ar/vep?id=12345",
            }
        }


class WorkflowListResponse(BaseModel):
    """Response for listing available workflows."""

    workflows: List[Dict[str, str]] = Field(..., description="Available workflows")
    count: int = Field(..., description="Number of available workflows")

    class Config:
        json_schema_extra = {
            "example": {
                "workflows": [
                    {
                        "id": "ccma_workflow",
                        "name": "CCMA Account Status",
                        "description": "Get CCMA account status and information",
                        "status": "ready",
                        "steps": "7",
                    }
                ],
                "count": 1,
            }
        }
