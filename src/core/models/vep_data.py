"""
VEP Data model - single responsibility for VEP entry structure.
"""

from typing import Optional

from pydantic import BaseModel, Field


class VEPData(BaseModel):
    """VEP entry data model containing all required fields for VEP generation."""

    fecha_expiracion: str = Field(..., description="Expiration date (YYYY-MM-DD)")
    nro_formulario: str = Field(..., description="Form number")
    cod_tipo_pago: str = Field(..., description="Payment type code")
    cuit: str = Field(..., description="CUIT number")
    concepto: str = Field(..., description="Tax concept")
    sub_concepto: str = Field(..., description="Sub concept")
    periodo_fiscal: str = Field(..., description="Fiscal period")
    importe: float = Field(..., description="Amount", gt=0)
    impuesto: str = Field(..., description="Tax code")
    # Additional fields for CCMA workflow
    periodo_desde: Optional[str] = Field(None, description="Period from (DD/MM/YYYY)")
    periodo_hasta: Optional[str] = Field(None, description="Period to (DD/MM/YYYY)")
    fecha_calculo: Optional[str] = Field(
        None, description="Calculation date (DD/MM/YYYY)"
    )
    descripcion: Optional[str] = Field(None, description="Payment description")

    class Config:
        json_schema_extra = {
            "example": {
                "fecha_expiracion": "2025-12-31",
                "nro_formulario": "1571",
                "cod_tipo_pago": "33",
                "cuit": "27120017808",
                "concepto": "19",
                "sub_concepto": "19",
                "periodo_fiscal": "202412",
                "importe": 105.00,
                "impuesto": "24",
            }
        }
