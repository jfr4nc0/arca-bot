"""
Simplified error handling utilities.
"""

import uuid

from fastapi import HTTPException, status
from fastapi.responses import JSONResponse


def handle_duplicate_transaction_error(
    transaction_hash: str, existing_exchange_id: str
) -> JSONResponse:
    """Handle duplicate transaction - specific case that needs special response."""
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={
            "transaction_hash": transaction_hash,
            "existing_exchange_id": existing_exchange_id,
            "error": "DuplicateTransaction",
            "message": "Transaction already exists",
        },
    )
