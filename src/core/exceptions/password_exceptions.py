"""
Password service related exceptions.
"""

from core.exceptions.base_exceptions import (
    BaseException,
    BusinessException,
    ExceptionCode,
    SystemException,
)


class PasswordNotFoundError(BusinessException):
    """Raised when password is not found for a given CUIT."""

    def __init__(self, cuit: str):
        self.cuit = cuit
        super().__init__(
            message=f"Password not found for CUIT: {cuit}",
            code=ExceptionCode.DATA_NOT_FOUND,
            details={"cuit": cuit},
        )


class PasswordFileError(SystemException):
    """Raised when there's an error with the password file."""

    def __init__(self, message: str, details: dict = None):
        super().__init__(
            message=f"Password file error: {message}",
            code=ExceptionCode.CONFIGURATION_ERROR,
            details=details or {},
        )


class PasswordDecryptionError(SystemException):
    """Raised when password file cannot be decrypted."""

    def __init__(self, details: dict = None):
        super().__init__(
            message="Failed to decrypt password file - invalid FERNET_KEY or corrupted file",
            code=ExceptionCode.SECURITY_VIOLATION,
            details=details or {},
        )


class PasswordServiceNotAvailableError(SystemException):
    """Raised when password service is not available (FERNET_KEY not configured)."""

    def __init__(self):
        super().__init__(
            message="Password service not available - FERNET_KEY not configured",
            code=ExceptionCode.CONFIGURATION_ERROR,
            details={"required_env_var": "FERNET_KEY"},
        )
