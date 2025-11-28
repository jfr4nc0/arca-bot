"""
API-specific exceptions for the ArcaAutoVep system.
Contains custom exceptions for different API error conditions.
"""

from core.exceptions.base_exceptions import BaseException, ExceptionCode


class APITransactionCreationError(BaseException):
    """Raised when a transaction cannot be created in the API layer."""

    def __init__(
        self,
        message: str = "Failed to create transaction",
        details: dict = None,
        original_exception: Exception = None,
    ):
        super().__init__(
            message=message,
            code=ExceptionCode.INTERNAL_ERROR,
            details=details or {},
            original_exception=original_exception,
        )


class APIWorkflowStartupError(BaseException):
    """Raised when a workflow cannot be started in the API layer."""

    def __init__(
        self,
        message: str = "Failed to start workflow",
        details: dict = None,
        original_exception: Exception = None,
    ):
        super().__init__(
            message=message,
            code=ExceptionCode.INTERNAL_ERROR,
            details=details or {},
            original_exception=original_exception,
        )
