"""
DDJJ workflow request model - collection validation only.
"""

from typing import List

from pydantic import BaseModel, Field

from api.models.requests.credentials import ARCACredentials
from api.models.requests.ddjj_entry import DDJJEntry


class DDJJWorkflowRequest(BaseModel):
    """Request for DDJJ workflow with credentials, entries and payment options."""

    credentials: ARCACredentials = Field(
        ..., alias="credenciales", description="ARCA authentication credentials"
    )
    entries: List[DDJJEntry] = Field(
        ...,
        alias="veps",
        description="List of DDJJ entries to include in single VEP file",
        min_items=1,
        max_items=100,
    )

    class Config:
        json_schema_extra = {
            "example": {
                "credentials": {
                    "cuit": "20123456789",
                    "contraseña": "your_arca_password",
                },
                "veps": [
                    {
                        "fecha_expiracion": "2025-12-31",
                        "nro_formulario": "1571",
                        "cod_tipo_pago": "33",
                        "cuit": "20123456789",
                        "concepto": "19",
                        "sub_concepto": "19",
                        "periodo_fiscal": "202412",
                        "importe": 300.00,
                        "impuesto": "24",
                    }
                ],
            }
        }
