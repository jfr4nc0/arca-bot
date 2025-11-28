"""
TTL calculation utilities for Redis cache expiration.
"""

from datetime import datetime
from typing import Optional, Union

from loguru import logger

from api.models.requests.ccma_request import CCMAWorkflowRequest
from api.models.requests.ddjj_request import DDJJWorkflowRequest


def calculate_ttl_from_entry_expiration(expiration_date: str) -> int:
    """
    Calculate TTL in seconds based on entry expiration date.

    Args:
        expiration_date: Entry-specific expiration date string

    Returns:
        TTL in seconds (minimum 300 seconds, default 3600 seconds)
    """
    if expiration_date:
        try:
            exp_dt = _parse_date(expiration_date)
            ttl_seconds = int((exp_dt - datetime.now()).total_seconds())
            logger.info(
                f"Calculated TTL: {ttl_seconds} seconds until {expiration_date}"
            )
            # Ensure minimum TTL of 5 minutes
            return max(ttl_seconds, 300)
        except (ValueError, TypeError) as e:
            logger.warning(
                f"Invalid expiration_date format: {expiration_date}, using default TTL. Error: {e}"
            )

    # Default TTL: 1 hour
    logger.debug("No expiration_date found, using default TTL of 3600 seconds")
    return 3600


def _parse_date(expiration_date: str) -> datetime:
    """Parse expiration date string into datetime object."""
    # Handle different date formats
    if "T" in expiration_date or "+" in expiration_date or "Z" in expiration_date:
        # ISO format with time
        return datetime.fromisoformat(expiration_date.replace("Z", "+00:00"))
    elif "/" in expiration_date:
        # DD/MM/YYYY format
        return datetime.strptime(expiration_date, "%d/%m/%Y")
    else:
        # Date-only format (YYYY-MM-DD)
        return datetime.strptime(expiration_date, "%Y-%m-%d")
