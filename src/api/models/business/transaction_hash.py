"""
Transaction hash generation - separated business logic.
"""

import hashlib

from api.models.requests.ccma_entry import CCMAEntry
from api.models.requests.ccma_request import CCMAWorkflowRequest
from api.models.requests.ddjj_entry import DDJJEntry
from api.models.requests.ddjj_request import DDJJWorkflowRequest
from api.models.requests.transaction_request import VEPTransactionRequest


def generate_transaction_hash(request: CCMAWorkflowRequest) -> str:
    """Generate a unique hash for duplicate transaction detection (DEPRECATED - use generate_ccma_workflow_hash)."""
    # For backward compatibility - delegate to new workflow hash function
    return generate_ccma_workflow_hash(request)


def generate_ddjj_entry_hash(entry: DDJJEntry) -> str:
    """Generate a unique hash for DDJJ entry duplicate detection."""
    # Create hash based on critical DDJJ parameters
    hash_data = f"{entry.cuit}|{entry.concept}|{entry.sub_concept}|{entry.fiscal_period}|{entry.amount}|{entry.tax_code}"

    # Include additional VEP fields
    hash_data += (
        f"|{entry.expiration_date}|{entry.form_number}|{entry.payment_type_code}"
    )

    # Generate SHA-256 hash
    return hashlib.sha256(hash_data.encode("utf-8")).hexdigest()


def generate_ddjj_workflow_hash(request: DDJJWorkflowRequest) -> str:
    """Generate a unique hash for DDJJ workflow - self-contained per VEP entry."""
    # Create hash based on all entries (each entry is self-contained)
    entries_data = []
    for entry in request.entries:
        entry_data = f"{entry.cuit}|{entry.concept}|{entry.sub_concept}|{entry.fiscal_period}|{entry.amount}|{entry.tax_code}"
        entry_data += (
            f"|{entry.expiration_date}|{entry.form_number}|{entry.payment_type_code}"
        )
        entries_data.append(entry_data)

    # Combine credentials with all entries
    hash_data = f"{request.credentials.cuit}|" + "|".join(sorted(entries_data))

    # Generate SHA-256 hash
    return hashlib.sha256(hash_data.encode("utf-8")).hexdigest()


def generate_ccma_entry_hash(entry: CCMAEntry) -> str:
    """Generate a unique hash for CCMA entry duplicate detection."""
    # Create hash based on critical CCMA parameters
    hash_data = f"{entry.period_from}|{entry.period_to}|{entry.calculation_date}"

    # Include optional parameters if present
    if entry.taxpayer_type:
        hash_data += f"|{entry.taxpayer_type}"
    if entry.tax_type:
        hash_data += f"|{entry.tax_type}"
    if entry.form_payment:
        hash_data += f"|{entry.form_payment}"
    if entry.expiration_date:
        hash_data += f"|{entry.expiration_date}"

    # Generate SHA-256 hash
    return hashlib.sha256(hash_data.encode("utf-8")).hexdigest()


def generate_ccma_workflow_hash(request: CCMAWorkflowRequest) -> str:
    """Generate a unique hash for CCMA workflow - self-contained per VEP entry."""
    # Create hash based on all entries (each entry is self-contained)
    entries_data = []
    for entry in request.entries:
        entry_data = f"{entry.period_from}|{entry.period_to}|{entry.calculation_date}|{entry.form_payment}|{entry.expiration_date}"

        # Include optional parameters if present
        if entry.taxpayer_type:
            entry_data += f"|{entry.taxpayer_type}"
        if entry.tax_type:
            entry_data += f"|{entry.tax_type}"

        entries_data.append(entry_data)

    # Combine credentials with all entries
    hash_data = f"{request.credentials.cuit}|" + "|".join(sorted(entries_data))

    # Generate SHA-256 hash
    return hashlib.sha256(hash_data.encode("utf-8")).hexdigest()


def generate_vep_hash(request: VEPTransactionRequest) -> str:
    """Generate VEP-specific hash for duplicate detection."""
    return generate_transaction_hash(request.ccma_request)
