"""
File utility functions - no interfaces needed for simple operations.
"""

import base64
import mimetypes
from pathlib import Path
from typing import Optional

from loguru import logger

from api.models.responses import FileData


def read_file_as_base64(file_path: str) -> Optional[str]:
    """Read file and return as base64 string."""
    try:
        path = Path(file_path)
        if not path.exists():
            logger.warning(f"File not found: {file_path}")
            return None

        file_content = path.read_bytes()
        return base64.b64encode(file_content).decode("utf-8")

    except Exception as e:
        logger.error(f"Error reading file {file_path}: {e}")
        return None


def get_content_type(file_path: str) -> str:
    """Get MIME type for file."""
    content_type, _ = mimetypes.guess_type(file_path)
    return content_type or "application/octet-stream"


def create_file_data(file_path: str) -> Optional[FileData]:
    """Create FileData model from file path."""
    base64_data = read_file_as_base64(file_path)
    if not base64_data:
        return None

    return FileData(
        filename=Path(file_path).name,
        content_type=get_content_type(file_path),
        data=base64_data,
    )
