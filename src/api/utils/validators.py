"""
Shared validation utilities for request models.
"""

from typing import Set

# Valid payment methods for VEP generation
ALLOWED_PAYMENT_METHODS: Set[str] = {
    "qr",
    "link",
    "pago_mis_cuentas",
    "inter_banking",
    "xn_group",
}


def validate_required_payment_method(payment_method: str) -> str:
    """
    Validate required payment method against allowed values.

    Args:
        payment_method: Required payment method string to validate

    Returns:
        The validated payment method

    Raises:
        ValueError: If payment method is not in allowed list
    """
    if payment_method not in ALLOWED_PAYMENT_METHODS:
        raise ValueError(
            f"Payment method must be one of: {', '.join(sorted(ALLOWED_PAYMENT_METHODS))}"
        )

    return payment_method
