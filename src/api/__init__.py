"""
API package for ArcaAutoVep Automatizations.
RESTful API implementation following SOLID principles.
"""

from api.exceptions import APITransactionCreationError, APIWorkflowStartupError

__all__ = [
    "APITransactionCreationError",
    "APIWorkflowStartupError",
]
