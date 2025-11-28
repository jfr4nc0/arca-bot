"""
DDJJ entry model - single responsibility for entry validation.
"""

from typing import Any, Dict

from pydantic import BaseModel, Field, validator

from api.utils.validators import validate_required_payment_method


class DDJJEntry(BaseModel):
    """Single DDJJ entry for VEP file generation."""

    form_payment: str = Field(
        ..., alias="metodo_pago", description="Payment method for VEP"
    )
    expiration_date: str = Field(
        ...,
        alias="fecha_expiracion",
        description="Expiration date in YYYY-MM-DD format",
        pattern=r"^\d{4}-\d{2}-\d{2}$",
    )
    form_number: str = Field(..., alias="nro_formulario", description="Form number")
    payment_type_code: str = Field(
        ..., alias="cod_tipo_pago", description="Payment type code"
    )
    cuit: str = Field(..., description="CUIT number", pattern=r"^\d{11}$")
    concept: str = Field(..., alias="concepto", description="Tax concept")
    sub_concept: str = Field(..., alias="sub_concepto", description="Sub concept")
    fiscal_period: str = Field(..., alias="periodo_fiscal", description="Fiscal period")
    amount: float = Field(..., alias="importe", description="Amount", gt=0)
    tax_code: str = Field(..., alias="impuesto", description="Tax code")

    @validator("expiration_date")
    def validate_expiration_date(cls, v):
        """Validate expiration date format."""
        try:
            from datetime import datetime

            datetime.strptime(v, "%Y-%m-%d")
            return v
        except ValueError:
            raise ValueError("Expiration date must be in YYYY-MM-DD format")

    @validator("form_payment")
    def validate_form_payment(cls, v):
        """Validate payment method against allowed values."""
        return validate_required_payment_method(v)

    class Config:
        populate_by_name = True
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
