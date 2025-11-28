"""
Utility for classifying errors as retryable or not using specific exception types.
"""

import sys

# Import built-in exception types
from socket import ConnectionAbortedError, ConnectionRefusedError, ConnectionResetError
from typing import Any, Dict

# Import Selenium and infrastructure exceptions for type checking
try:
    from selenium.common.exceptions import (
        BrowserNotConnectedException,
        NoSuchDriverException,
        SessionNotCreatedException,
        WebDriverException,
    )

    HAS_SELENIUM = True
except ImportError:
    # Fallback if Selenium is not available
    class SessionNotCreatedException(Exception):
        pass

    class WebDriverException(Exception):
        pass

    class NoSuchDriverException(Exception):
        pass

    class BrowserNotConnectedException(Exception):
        pass

    HAS_SELENIUM = False

try:
    from http.client import ServiceUnavailable

    HAS_HTTP_CLIENT = True
except ImportError:

    class ServiceUnavailable(Exception):
        pass

    HAS_HTTP_CLIENT = False


def is_retryable_error(error_input: Exception) -> bool:
    """
    Check if an exception indicates a retryable error based on its type.

    Args:
        error_input: Exception object to check

    Returns:
        bool: True if error is retryable, False otherwise
    """
    # Only accept Exception objects, not error message strings
    # The anti-pattern of parsing error messages is completely eliminated
    # Check using specific exception types
    try:
        from core.exceptions import BrowserSessionException, InfrastructureException

        # Check if it's a known retryable exception type
        if isinstance(error_input, (InfrastructureException, BrowserSessionException)):
            return True

    except ImportError:
        pass  # Continue to check built-in exception types

    # Check for common Selenium and infrastructure exceptions using exact type matching
    # This eliminates the anti-pattern of substring matching in exception type names
    retryable_types = (
        TimeoutError,
        ConnectionRefusedError,
        ConnectionAbortedError,
        ConnectionResetError,
        ServiceUnavailable,
        SessionNotCreatedException,
        WebDriverException,
        NoSuchDriverException,
        BrowserNotConnectedException,
    )

    if isinstance(error_input, retryable_types):
        return True

    # Check built-in exception types for connectivity issues
    if isinstance(
        error_input,
        (
            ConnectionRefusedError,
            ConnectionAbortedError,
            ConnectionResetError,
            TimeoutError,
        ),
    ):
        return True

    return False


def has_retryable_error(errors: Dict[str, Any]) -> bool:
    """
    Check if any error in a dictionary of errors is retryable.

    Args:
        errors: Dictionary of errors to check (should contain Exception objects only)

    Returns:
        bool: True if any error is retryable, False otherwise
    """
    if not errors:
        return False

    for error_detail in errors.values():
        if isinstance(error_detail, Exception) and is_retryable_error(error_detail):
            return True
        elif isinstance(error_detail, dict):
            # Recursively check nested error details
            if has_retryable_error(error_detail):
                return True
        elif isinstance(error_detail, list):
            # Check if it's a list of errors
            for item in error_detail:
                if isinstance(item, Exception) and is_retryable_error(item):
                    return True
                elif isinstance(item, dict) and has_retryable_error(item):
                    return True

    return False
