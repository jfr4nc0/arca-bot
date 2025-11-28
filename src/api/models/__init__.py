"""
API models module - organized by Single Responsibility Principle.
"""

# Business logic - transaction hashing
from api.models.business import generate_transaction_hash, generate_vep_hash

# Request models - input validation and structure
from api.models.requests import CCMAWorkflowRequest, VEPTransactionRequest

# Response models - output serialization
from api.models.responses import (
    ErrorResponse,
    FileData,
    HealthCheckResponse,
    VEPGenerationResponse,
    WorkflowExecutionResponse,
    WorkflowListResponse,
    WorkflowStatusResponse,
)

__all__ = [
    # Requests
    "CCMAWorkflowRequest",
    "VEPTransactionRequest",
    # Responses
    "FileData",
    "WorkflowExecutionResponse",
    "WorkflowStatusResponse",
    "VEPGenerationResponse",
    "ErrorResponse",
    "HealthCheckResponse",
    "WorkflowListResponse",
    # Business logic
    "generate_transaction_hash",
    "generate_vep_hash",
]
