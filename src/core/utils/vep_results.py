"""
VEP result processing utilities for workflow outputs.
"""

import base64
import mimetypes
from pathlib import Path
from typing import Any, Dict, Optional
from uuid import UUID

from loguru import logger


def _is_serializable(value: Any) -> bool:
    """Check if a value can be serialized to JSON."""
    try:
        # Check for basic JSON-serializable types
        if isinstance(value, (str, int, float, bool, type(None))):
            return True

        # Check for collections of serializable types
        if isinstance(value, (list, tuple)):
            return all(_is_serializable(item) for item in value)

        if isinstance(value, dict):
            return all(
                isinstance(k, str) and _is_serializable(v) for k, v in value.items()
            )

        # Exclude complex objects like service instances
        return False
    except Exception:
        return False


def _create_file_data_dict(file_path: str) -> Optional[Dict[str, str]]:
    """Create file data dictionary with base64 content."""
    try:
        path = Path(file_path)
        if not path.exists():
            logger.warning(f"File not found: {file_path}")
            return None

        # Read file content
        file_content = path.read_bytes()
        base64_content = base64.b64encode(file_content).decode("utf-8")

        # Get MIME type
        content_type, _ = mimetypes.guess_type(file_path)
        mime_type = content_type or "application/octet-stream"

        return {
            "filename": path.name,
            "content_type": mime_type,
            "data": base64_content,
        }

    except Exception as e:
        logger.error(f"Error creating file data for {file_path}: {e}")
        return None


def process_vep_results(
    workflow_results: Dict[str, Any],
    exchange_id: Optional[str] = None,
    transaction_hash: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Process VEP workflow results into standardized format with base64 files.

    Args:
        workflow_results: Raw workflow results dictionary
        exchange_id: Optional exchange ID (can be UUID or string)
        transaction_hash: Optional transaction hash

    Returns:
        Dictionary with processed results including base64 encoded files
    """
    try:
        processed_results = {}

        # Add identifiers if provided
        if exchange_id:
            processed_results["exchange_id"] = str(exchange_id)
        if transaction_hash:
            processed_results["transaction_hash"] = transaction_hash

        # Process PDF file if available
        if "vep_pdf_path" in workflow_results:
            pdf_path = workflow_results["vep_pdf_path"]
            if pdf_path:
                pdf_data = _create_file_data_dict(pdf_path)
                if pdf_data:
                    processed_results["pdf"] = pdf_data
                    logger.debug(
                        f"Added PDF to processed results: {pdf_data['filename']}"
                    )

        # Process QR/PNG files (find first QR path)
        qr_files = [
            key
            for key in workflow_results.keys()
            if "qr" in key.lower() and "path" in key
        ]
        for qr_key in qr_files:
            qr_path = workflow_results[qr_key]
            if qr_path and Path(qr_path).exists():
                png_data = _create_file_data_dict(qr_path)
                if png_data:
                    processed_results["png"] = png_data
                    logger.debug(
                        f"Added PNG to processed results: {png_data['filename']}"
                    )
                    break  # Only process first QR file found

        # Include payment URL if available
        if "payment_url" in workflow_results:
            processed_results["payment_url"] = workflow_results["payment_url"]

        # Include other serializable non-file results
        excluded_keys = {"payment_url", "vep_pdf_filename", "vep_qr_filename"}

        for k, v in workflow_results.items():
            if (
                not k.endswith("_path")  # Exclude file paths
                and k not in excluded_keys  # Exclude already processed keys
                and not k.endswith("_service")  # Exclude service objects
                and _is_serializable(v)  # Only include serializable types
            ):
                processed_results[k] = v

        return processed_results

    except Exception as e:
        logger.error(f"Error processing VEP workflow results: {e}")
        return {
            "error": str(e),
            "exchange_id": str(exchange_id) if exchange_id else None,
            "transaction_hash": transaction_hash,
        }


def extract_file_paths(workflow_results: Dict[str, Any]) -> Dict[str, str]:
    """Extract file paths from workflow results."""
    file_paths = {}

    # Extract PDF path
    if "vep_pdf_path" in workflow_results and workflow_results["vep_pdf_path"]:
        file_paths["pdf"] = workflow_results["vep_pdf_path"]

    # Extract QR/PNG paths
    qr_files = [
        key for key in workflow_results.keys() if "qr" in key.lower() and "path" in key
    ]
    for qr_key in qr_files:
        if workflow_results[qr_key]:
            file_paths["png"] = workflow_results[qr_key]
            break

    return file_paths
