"""
Infrastructure-specific exceptions for the ArcaAutoVep system.
"""

from core.exceptions.base_exceptions import BaseException, ExceptionCode


class InfrastructureException(BaseException):
    """Raised when there's an infrastructure failure that should be retried."""

    def __init__(
        self,
        message: str = "Infrastructure failure - service unavailable or overloaded",
        error_type: str = None,
        details: dict = None,
        original_exception: Exception = None,
    ):
        exception_details = details or {}
        exception_details["error_type"] = error_type
        super().__init__(
            message=message,
            code=ExceptionCode.SERVICE_UNAVAILABLE,  # Use the most general code
            details=exception_details,
            original_exception=original_exception,
        )


class BrowserSessionException(BaseException):
    """Raised when there's a browser session-related failure."""

    def __init__(
        self,
        message: str = "Browser session creation failed",
        session_details: dict = None,
        original_exception: Exception = None,
    ):
        details = session_details or {}
        super().__init__(
            message=message,
            code=ExceptionCode.SESSION_POOL_EXHAUSTED,  # Covers all session issues
            details=details,
            original_exception=original_exception,
        )
