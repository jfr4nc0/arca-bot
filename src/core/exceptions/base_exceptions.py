"""
Base exception classes for the ArcaAutoVep system.
"""

from enum import Enum
from typing import Optional


class ExceptionCode(Enum):
    """Enumeration of all possible exception codes."""

    # Infrastructure errors (INFRA_XXXX)
    SESSION_POOL_EXHAUSTED = "INFRA_1001"
    SELENIUM_GRID_UNAVAILABLE = "INFRA_1002"
    SERVICE_UNAVAILABLE = "INFRA_1003"
    CONNECTION_REFUSED = "INFRA_1004"
    TIMEOUT_ERROR = "INFRA_1005"
    BROWSER_STARTUP_FAILED = "INFRA_1006"
    GRID_CONNECTION_ERROR = "INFRA_1007"
    DATABASE_CONNECTION_ERROR = "INFRA_1008"
    NETWORK_ERROR = "INFRA_1009"
    RESOURCE_EXHAUSTED = "INFRA_1010"

    # Business rule errors (BIZ_XXXX)
    AUTHENTICATION_FAILED = "BIZ_2001"
    AUTHORIZATION_FAILED = "BIZ_2002"
    VALIDATION_ERROR = "BIZ_2003"
    DATA_NOT_FOUND = "BIZ_2004"
    BUSINESS_RULE_VIOLATION = "BIZ_2005"
    PAYMENT_PROCESSING_ERROR = "BIZ_2006"
    INVALID_STATE = "BIZ_2007"
    DUPLICATE_RESOURCE = "BIZ_2008"
    RATE_LIMIT_EXCEEDED = "BIZ_2009"
    QUOTA_EXCEEDED = "BIZ_2010"

    # Workflow errors (WF_XXXX)
    WORKFLOW_EXECUTION_ERROR = "WF_3001"
    STEP_EXECUTION_FAILED = "WF_3002"
    WORKFLOW_TIMEOUT = "WF_3003"
    INVALID_WORKFLOW_STATE = "WF_3004"
    WORKFLOW_CANCELLED = "WF_3005"

    # System errors (SYS_XXXX)
    CONFIGURATION_ERROR = "SYS_4001"
    SECURITY_VIOLATION = "SYS_4002"
    SYSTEM_UNAVAILABLE = "SYS_4003"
    INTERNAL_ERROR = "SYS_4004"
    FEATURE_NOT_IMPLEMENTED = "SYS_4005"

    # External service errors (EXT_XXXX)
    EXTERNAL_API_ERROR = "EXT_5001"
    EXTERNAL_SERVICE_TIMEOUT = "EXT_5002"
    EXTERNAL_SERVICE_UNAVAILABLE = "EXT_5003"
    EXTERNAL_AUTH_FAILED = "EXT_5004"
    EXTERNAL_RATE_LIMITED = "EXT_5005"


class BaseException(Exception):
    """Base exception for the ArcaAutoVep system."""

    def __init__(
        self,
        message: str,
        code: ExceptionCode,
        details: Optional[dict] = None,
        original_exception: Optional[Exception] = None,
    ):
        super().__init__(message)
        self.message = message
        self.code = code.value
        self.details = details or {}
        self.original_exception = original_exception

    def __str__(self):
        return f"[{self.code}] {self.message}"

    def to_dict(self):
        """Convert exception to dictionary for serialization."""
        return {
            "code": self.code,
            "message": self.message,
            "details": self.details,
            "original_exception_type": (
                type(self.original_exception).__name__
                if self.original_exception
                else None
            ),
        }


class WorkflowException(BaseException):
    """Base exception for workflow-related errors."""

    pass


class BusinessException(BaseException):
    """Base exception for business rule violations."""

    pass


class SystemException(BaseException):
    """Base exception for system-level errors."""

    pass


class ExternalServiceException(BaseException):
    """Base exception for external service-related errors."""

    pass
