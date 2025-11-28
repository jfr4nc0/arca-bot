"""
Test suite for password service.
"""

import os
import sys

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.exceptions.password_exceptions import (
    PasswordDecryptionError,
    PasswordFileError,
    PasswordNotFoundError,
    PasswordServiceNotAvailableError,
)
from core.services.system.password_service import PasswordService


def test_password_service_with_real_file():
    """Test password service with actual encrypted Excel file."""
    # Get FERNET_KEY from environment
    fernet_key = os.getenv("FERNET_KEY")
    if not fernet_key:
        print("FERNET_KEY environment variable not set, skipping test")
        return

    try:
        # Initialize service with real file
        service = PasswordService(fernet_key, "./resources/claves/claves.xlsx")

        # Test basic functionality
        stats = service.get_stats()
        assert stats["cache_loaded"] is True
        assert stats["total_passwords"] > 0

        print(
            f"✓ Test passed: Loaded {stats['total_passwords']} passwords from encrypted Excel file"
        )

    except Exception as e:
        print(f"✗ Test failed: {e}")
        raise


if __name__ == "__main__":
    print("Running password service test...")
    test_password_service_with_real_file()
    print("Test completed!")
