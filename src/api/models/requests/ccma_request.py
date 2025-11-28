"""
CCMA workflow request model - focused on input validation only.
"""

from datetime import datetime
from typing import List

from pydantic import BaseModel, Field

from api.models.requests.ccma_entry import CCMAEntry
from api.models.requests.credentials import ARCACredentials


class CCMAWorkflowRequest(BaseModel):
    """Request model for CCMA workflow execution - validation only."""

    credentials: ARCACredentials = Field(
        ..., alias="credenciales", description="ARCA authentication credentials"
    )
    entries: List[CCMAEntry] = Field(
        ...,
        alias="veps",
        description="List of CCMA entries to include in VEP generation",
        min_items=1,
        max_items=100,
    )

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}
        json_schema_extra = {
            "example": {
                "credenciales": {
                    "cuit": "20429994323",
                    "contraseña": "your_arca_password",
                },
                "veps": [
                    {
                        "periodo_desde": "01/2023",
                        "periodo_hasta": "12/2025",
                        "fecha_calculo": "15/09/2025",
                        "tipo_contribuyente": "Monotributo",
                        "impuesto": "IVA",
                        "metodo_pago": "qr",
                    }
                ],
            }
        }
