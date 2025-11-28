"""
Core services package for ArcaAutoVep RPA system.
Contains all the service implementations for browser automation and business logic.
"""

# Browser services
from core.services.browser.browser import BrowserManager

# System services
from core.services.system.file_handler import FileHandler

__all__ = [
    "BrowserManager",
    "FileHandler",
]
