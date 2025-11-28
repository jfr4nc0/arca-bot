"""
CCMA workflow execution response model - single responsibility for workflow response.
"""

import uuid
from typing import List, Optional

from pydantic import BaseModel, Field

from api.models.responses.ccma_entry_status import CCMAEntryStatus


class CCMAWorkflowExecutionResponse(BaseModel):
    """Response for CCMA workflow execution."""

    exchange_id: Optional[uuid.UUID] = Field(
        None, description="Exchange ID for new workflow (if any entries processed)"
    )
    processed_entries: List[CCMAEntryStatus] = Field(
        ..., description="Entries that were processed in new workflow"
    )
    duplicate_entries: List[CCMAEntryStatus] = Field(
        ..., description="Entries that were duplicates of existing workflows"
    )
    vep_file_path: Optional[str] = Field(
        None, description="Path to generated VEP file (if any entries processed)"
    )
    total_entries: int = Field(..., description="Total number of entries in request")
    processed_count: int = Field(..., description="Number of new entries processed")
    duplicate_count: int = Field(..., description="Number of duplicate entries found")

    class Config:
        json_schema_extra = {
            "example": {
                "exchange_id": "123e4567-e89b-12d3-a456-426614174000",
                "processed_entries": [
                    {
                        "period_from": "01/2023",
                        "period_to": "12/2025",
                        "calculation_date": "15/09/2025",
                        "taxpayer_type": "Monotributo",
                        "tax_type": "IVA",
                        "transaction_hash": "abc123def456",
                        "status": "new",
                        "existing_exchange_id": None,
                    }
                ],
                "duplicate_entries": [],
                "vep_file_path": None,
                "total_entries": 1,
                "processed_count": 1,
                "duplicate_count": 0,
            }
        }
