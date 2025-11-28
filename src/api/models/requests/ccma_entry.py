"""
CCMA entry model - single responsibility for entry validation.
"""

from typing import Optional

from pydantic import BaseModel, Field, validator

from api.utils.validators import validate_required_payment_method


class CCMAEntry(BaseModel):
    """Single CCMA entry for VEP generation."""

    period_from: str = Field(
        ...,
        alias="periodo_desde",
        description="Start period in MM/YYYY format",
        pattern=r"^\d{2}/\d{4}$",
    )
    period_to: str = Field(
        ...,
        alias="periodo_hasta",
        description="End period in MM/YYYY format",
        pattern=r"^\d{2}/\d{4}$",
    )
    calculation_date: str = Field(
        ...,
        alias="fecha_calculo",
        description="Calculation date in DD/MM/YYYY format",
        pattern=r"^\d{2}/\d{2}/\d{4}$",
    )
    form_payment: str = Field(
        ..., alias="metodo_pago", description="Payment method for VEP"
    )
    expiration_date: str = Field(
        ...,
        alias="fecha_expiracion",
        description="Transaction expiration date in DD/MM/YYYY format",
        pattern=r"^\d{2}/\d{2}/\d{4}$",
    )

    # Optional parameters
    taxpayer_type: Optional[str] = Field(
        None,
        alias="tipo_contribuyente",
        description="Type of taxpayer (e.g., 'IVA', 'Monotributo')",
    )
    tax_type: Optional[str] = Field(
        None, alias="impuesto", description="Tax type (e.g., 'IVA', '021')"
    )
    include_interests: bool = Field(
        False,
        alias="incluir_intereses",
        description="Whether to include interests in VEP generation",
    )

    @validator("period_from", "period_to")
    def validate_period_format(cls, v):
        """Validate period format and logical constraints."""
        try:
            month, year = v.split("/")
            month_int = int(month)
            year_int = int(year)

            if not (1 <= month_int <= 12):
                raise ValueError("Month must be between 01 and 12")

            if not (2000 <= year_int <= 2030):
                raise ValueError("Year must be between 2000 and 2030")

            return v
        except ValueError as e:
            raise ValueError(f"Invalid period format: {e}")

    @validator("calculation_date")
    def validate_calculation_date(cls, v):
        """Validate calculation date format."""
        try:
            from datetime import datetime

            datetime.strptime(v, "%d/%m/%Y")
            return v
        except ValueError:
            raise ValueError("Calculation date must be in DD/MM/YYYY format")

    @validator("expiration_date")
    def validate_expiration_date(cls, v):
        """Validate expiration date format."""
        try:
            from datetime import datetime

            datetime.strptime(v, "%d/%m/%Y")
            return v
        except ValueError:
            raise ValueError("Expiration date must be in DD/MM/YYYY format")

    @validator("form_payment")
    def validate_form_payment(cls, v):
        """Validate payment method against allowed values."""
        return validate_required_payment_method(v)

    class Config:
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "periodo_desde": "01/2023",
                "periodo_hasta": "12/2025",
                "fecha_calculo": "19/09/2025",
                "tipo_contribuyente": "Monotributo",
                "impuesto": "IVA",
                "metodo_pago": "qr",
                "fecha_expiracion": "2025-12-31",
                "incluir_intereses": True,
            }
        }
