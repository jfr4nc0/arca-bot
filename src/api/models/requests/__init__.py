"""
Request models module - organized by responsibility.
"""

from api.models.requests.ccma_request import CCMAWorkflowRequest
from api.models.requests.ddjj_entry import DDJJEntry
from api.models.requests.ddjj_request import DDJJWorkflowRequest
from api.models.requests.transaction_request import VEPTransactionRequest

__all__ = [
    "CCMAWorkflowRequest",
    "DDJJEntry",
    "DDJJWorkflowRequest",
    "VEPTransactionRequest",
]
