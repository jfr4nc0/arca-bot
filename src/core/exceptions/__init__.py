"""
Exception module for the ArcaAutoVep system.
Contains custom exceptions for different error types.
"""

# Import base exception classes
from core.exceptions.base_exceptions import BaseException as BaseArcaAutoVepException
from core.exceptions.base_exceptions import (
    BusinessException,
    ExceptionCode,
    ExternalServiceException,
    SystemException,
    WorkflowException,
)

# Import infrastructure exceptions (simplified hierarchy)
from core.exceptions.infrastructure_exceptions import (
    BrowserSessionException,
    InfrastructureException,
)

__all__ = [
    "BaseArcaAutoVepException",
    "InfrastructureException",
    "WorkflowException",
    "BusinessException",
    "SystemException",
    "ExternalServiceException",
    "ExceptionCode",
    "BrowserSessionException",
]
