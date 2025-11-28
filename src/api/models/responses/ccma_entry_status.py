"""
CCMA entry status model - tracks individual entry processing status.
"""

import uuid
from typing import Optional

from pydantic import BaseModel, Field


class CCMAEntryStatus(BaseModel):
    """Status of a single CCMA entry in workflow execution."""

    period_from: str = Field(..., description="Start period of the CCMA entry")
    period_to: str = Field(..., description="End period of the CCMA entry")
    calculation_date: str = Field(..., description="Calculation date of the CCMA entry")
    taxpayer_type: Optional[str] = Field(None, description="Type of taxpayer")
    tax_type: Optional[str] = Field(None, description="Tax type")
    transaction_hash: str = Field(..., description="Transaction hash for deduplication")
    status: str = Field(..., description="Status: 'new', 'duplicate', 'failed'")
    existing_exchange_id: Optional[uuid.UUID] = Field(
        None, description="Exchange ID of existing transaction (if duplicate)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "period_from": "01/2023",
                "period_to": "12/2025",
                "calculation_date": "15/09/2025",
                "taxpayer_type": "Monotributo",
                "tax_type": "IVA",
                "transaction_hash": "abc123def456",
                "status": "new",
                "existing_exchange_id": None,
            }
        }
