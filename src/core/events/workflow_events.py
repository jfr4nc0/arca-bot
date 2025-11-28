"""
Workflow event models for Kafka messaging.
"""

import base64
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional
from uuid import UUID

from loguru import logger


@dataclass
class WorkflowFinishedEvent:
    """Event published when a workflow finishes (success or failure)."""

    exchange_id: str
    workflow_type: str  # ccma_workflow, ddjj_workflow
    timestamp: datetime
    success: bool
    response: Optional[Dict[str, Any]] = None  # WorkflowStatusResponse when successful
    error_details: Optional[str] = None  # Error message when failed
    pdf_content: Optional[str] = (
        None  # Base64 encoded PDF content for downstream processing
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        data = asdict(self)
        data["timestamp"] = self.timestamp.isoformat()
        return data

    def add_pdf_from_file(self, pdf_path: str) -> bool:
        """
        Add PDF content from file path.

        Args:
            pdf_path: Path to the PDF file

        Returns:
            True if PDF was successfully encoded, False otherwise
        """
        try:
            pdf_file = Path(pdf_path)
            if not pdf_file.exists():
                logger.warning(f"PDF file not found: {pdf_path}")
                return False

            # Read PDF file and encode as base64
            with open(pdf_file, "rb") as f:
                pdf_bytes = f.read()

            self.pdf_content = base64.b64encode(pdf_bytes).decode("utf-8")
            logger.debug(f"PDF content added to event from: {pdf_path}")
            return True

        except Exception as e:
            logger.error(f"Error adding PDF content from file {pdf_path}: {e}")
            return False

    def get_pdf_size_kb(self) -> float:
        """
        Get the size of the PDF content in KB.

        Returns:
            Size in KB, or 0 if no PDF content
        """
        if not self.pdf_content:
            return 0.0

        # Base64 encoding increases size by ~33%, so decode to get original size
        try:
            decoded_size = len(base64.b64decode(self.pdf_content))
            return decoded_size / 1024.0
        except Exception:
            return 0.0
