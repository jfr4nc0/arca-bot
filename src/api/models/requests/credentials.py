"""
ARCA authentication credentials model - reusable across workflows.
"""

from typing import Optional

from pydantic import BaseModel, Field


class ARCACredentials(BaseModel):
    """ARCA authentication credentials for all workflows."""

    cuit: str = Field(
        ..., description="CUIT number for ARCA authentication", pattern=r"^\d{11}$"
    )
    password: Optional[str] = Field(
        None,
        alias="contraseña",
        description="Password for ARCA authentication (optional when handled by service)",
        min_length=1,
    )

    class Config:
        json_schema_extra = {
            "example": {"cuit": "20123456789", "contraseña": "your_arca_password"}
        }
