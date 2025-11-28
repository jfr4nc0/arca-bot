"""
Test suite for simplified services.
"""

import os
import sys
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestSimplePaymentHandler:
    """Test simplified payment handler."""

    def test_payment_methods_validation(self):
        """Test payment method validation."""
        from core.services.browser.browser import BrowserManager
        from core.services.ccma.payment_handler import PaymentHandler

        browser_mock = Mock(spec=BrowserManager)
        handler = PaymentHandler(browser_mock)

        # Test valid payment methods
        assert handler.validate_payment_method("qr") == True
        assert handler.validate_payment_method("link") == True
        assert handler.validate_payment_method("pago_mis_cuentas") == True

        # Test invalid payment method
        assert handler.validate_payment_method("invalid_method") == False

    def test_get_default_payment_method(self):
        """Test getting default payment method."""
        from core.services.browser.browser import BrowserManager
        from core.services.ccma.payment_handler import PaymentHandler

        browser_mock = Mock(spec=BrowserManager)
        handler = PaymentHandler(browser_mock)

        default_method = handler.get_default_payment_method()
        assert default_method == "qr"


class TestSimpleFileHandler:
    """Test simplified file handler."""

    def test_ensure_directory(self):
        """Test directory creation."""
        from core.services.system.file_handler import FileHandler

        handler = FileHandler()
        test_dir = Path("/tmp/test_directory")

        # Test creating directory
        result = handler.ensure_directory(test_dir)
        assert result == True
        assert test_dir.exists()

        # Clean up
        test_dir.rmdir()

    def test_get_files_snapshot(self):
        """Test getting file snapshots."""
        from core.services.system.file_handler import FileHandler

        handler = FileHandler()
        test_dir = Path("/tmp/test_snapshot")

        # Create test directory
        test_dir.mkdir(exist_ok=True)

        # Test with empty directory
        files = handler.get_files_snapshot(test_dir, "*.txt")
        assert isinstance(files, set)

        # Clean up
        test_dir.rmdir()

    def test_save_text_file(self):
        """Test saving text files."""
        from core.services.system.file_handler import FileHandler

        handler = FileHandler()
        test_file = Path("/tmp/test_file.txt")

        # Test saving content
        result = handler.save_text_file("test content", test_file)
        assert result == True
        assert test_file.exists()

        # Verify content
        with open(test_file, "r") as f:
            content = f.read()
        assert content == "test content"

        # Clean up
        test_file.unlink()


class TestSimpleVEPService:
    """Test simplified VEP service."""

    def test_payment_method_validation(self):
        """Test payment method validation in VEP service."""
        from core.services.browser.browser import BrowserManager
        from core.services.ccma.vep_service import VEPService

        browser_mock = Mock(spec=BrowserManager)
        service = VEPService(browser_mock)

        # Test valid payment methods
        assert service.validate_payment_method("qr") == True
        assert service.validate_payment_method("link") == True

        # Test invalid payment method
        assert service.validate_payment_method("invalid") == False

    def test_get_default_payment_method(self):
        """Test getting default payment method."""
        from core.services.browser.browser import BrowserManager
        from core.services.ccma.vep_service import VEPService

        browser_mock = Mock(spec=BrowserManager)
        service = VEPService(browser_mock)

        default_method = service.get_default_payment_method()
        assert default_method == "qr"
