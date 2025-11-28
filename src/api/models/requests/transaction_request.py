"""
Transaction-related request models with business logic.
"""

from typing import Optional

from pydantic import BaseModel, Field

from api.models.requests.ccma_request import CCMAWorkflowRequest


class VEPTransactionRequest(BaseModel):
    """Specific request model for VEP transactions with enhanced validation."""

    ccma_request: CCMAWorkflowRequest
    priority: Optional[str] = Field(
        "normal", description="Execution priority", pattern=r"^(low|normal|high)$"
    )
    callback_url: Optional[str] = Field(
        None, description="URL to notify when workflow completes"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "ccma_request": {
                    "cuit": "20429994323",
                    "period_from": "01/2023",
                    "period_to": "12/2025",
                    "calculation_date": "15/09/2025",
                    "form_payment": "qr",
                },
                "priority": "high",
                "callback_url": "https://client-system.com/webhook/ccma-completed",
            }
        }
