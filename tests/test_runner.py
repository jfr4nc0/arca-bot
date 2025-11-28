#!/usr/bin/env python3
"""
Simple test runner for the project.
"""

import os
import subprocess
import sys


def run_tests():
    """Run all tests using pytest."""
    print("Running tests with pytest...")

    try:
        # Run pytest with coverage
        result = subprocess.run(
            [
                "poetry",
                "run",
                "pytest",
                "-v",
                "--cov=core",
                "--cov-report=term-missing",
                "tests/",
            ],
            check=True,
        )

        print("\nAll tests passed!")
        return True

    except subprocess.CalledProcessError as e:
        print(f"\nTests failed with exit code {e.returncode}")
        return False


def run_unit_tests():
    """Run unit tests only."""
    print("Running unit tests...")

    try:
        result = subprocess.run(
            [
                "poetry",
                "run",
                "pytest",
                "-v",
                "tests/test_services.py",
                "tests/test_workflows.py",
            ],
            check=True,
        )

        print("\nUnit tests passed!")
        return True

    except subprocess.CalledProcessError as e:
        print(f"\nUnit tests failed with exit code {e.returncode}")
        return False


def main():
    """Main test runner."""
    if len(sys.argv) > 1:
        if sys.argv[1] == "unit":
            success = run_unit_tests()
        else:
            print("Usage: python test_runner.py [unit]")
            return 1
    else:
        success = run_tests()

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
