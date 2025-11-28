"""
DDJJ workflow execution response model - single responsibility for workflow response.
"""

import uuid
from typing import List, Optional

from pydantic import BaseModel, Field

from api.models.responses.ddjj_entry_status import DDJJEntryStatus


class DDJJWorkflowExecutionResponse(BaseModel):
    """Response for DDJJ workflow execution."""

    exchange_id: Optional[uuid.UUID] = Field(
        None, description="Exchange ID for new workflow (if any entries processed)"
    )
    processed_entries: List[DDJJEntryStatus] = Field(
        ..., description="Entries that were processed in new workflow"
    )
    duplicate_entries: List[DDJJEntryStatus] = Field(
        ..., description="Entries that were duplicates of existing workflows"
    )
    vep_file_path: Optional[str] = Field(
        None, description="Path to generated VEP file (if any entries processed)"
    )
    total_entries: int = Field(..., description="Total number of entries in request")
    processed_count: int = Field(..., description="Number of new entries processed")
    duplicate_count: int = Field(..., description="Number of duplicate entries found")
