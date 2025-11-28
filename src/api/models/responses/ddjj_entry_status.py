"""
DDJJ entry status model - single responsibility for entry status representation.
"""

import uuid
from typing import Optional

from pydantic import BaseModel, Field


class DDJJEntryStatus(BaseModel):
    """Status of a single DDJJ entry processing."""

    cuit: str = Field(..., description="CUIT for this entry")
    transaction_hash: str = Field(..., description="Transaction hash for this entry")
    status: str = Field(..., description="Processing status: 'new', 'duplicate'")
    existing_exchange_id: Optional[uuid.UUID] = Field(
        None, description="Exchange ID if entry was duplicate"
    )
