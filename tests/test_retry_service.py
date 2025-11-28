#!/usr/bin/env python3
"""
Test script for the retry service implementation.
"""

import os
import sys

# Add the project root to the Python path
project_root = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(project_root)
sys.path.insert(0, parent_dir)

# Change to the project directory
os.chdir(parent_dir)

from core.utils.error_classifier import has_retryable_error, is_retryable_error


def test_error_classifier():
    """Test the error classifier utility."""
    print("Testing error classifier...")

    # Test retryable errors
    retryable_errors = [
        "Timeout occurred while connecting to server",
        "503 Service Unavailable",
        "504 Gateway Timeout",
        "Connection refused by server",
        "Network error occurred",
        "Page load timeout exceeded",
    ]

    for error in retryable_errors:
        result = is_retryable_error(error)
        print(f"  '{error}' -> {result}")
        assert result == True, f"Expected {error} to be retryable"

    # Test non-retryable errors
    non_retryable_errors = [
        "Invalid credentials provided",
        "User not found",
        "Permission denied",
        "File not found",
    ]

    for error in non_retryable_errors:
        result = is_retryable_error(error)
        print(f"  '{error}' -> {result}")
        assert result == False, f"Expected {error} to be non-retryable"

    print("Error classifier tests passed!\n")


def main():
    """Main test function."""
    print("Running retry service tests...\n")

    # Test error classifier
    test_error_classifier()

    print("All tests passed!")


if __name__ == "__main__":
    main()
