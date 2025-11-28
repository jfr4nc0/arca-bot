#!/usr/bin/env python3
"""
Simple helper to manually test Google Drive uploads using existing artifacts.

Usage:
    python scripts/google_drive_upload_test.py

The script looks for any PDF under resources/pdf and PNG under resources/qr
and uploads them to the configured Google Drive folder using the Drive service.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Iterable, List

from loguru import logger

# Ensure src/ is on sys.path when running the script directly
REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = REPO_ROOT / "src"
if SRC_PATH.exists():
    sys.path.append(str(SRC_PATH))

from core.config import config  # noqa: E402
from core.services.google_drive.drive_service import GoogleDriveService  # noqa: E402


def _collect_test_files() -> List[Path]:
    """Find candidate PDF/PNG files under resources directories."""
    targets: List[Path] = []

    pdf_dir = REPO_ROOT / "resources" / "pdf"
    if pdf_dir.exists():
        targets.extend(sorted(pdf_dir.glob("*.pdf")))

    qr_dir = REPO_ROOT / "resources" / "qr"
    if qr_dir.exists():
        targets.extend(sorted(qr_dir.glob("*.png")))

    return targets


def _upload_files(service: GoogleDriveService, files: Iterable[Path]) -> None:
    """Upload each provided file to Drive."""
    for file_path in files:
        file_type = "pdf" if file_path.suffix.lower() == ".pdf" else "qr"
        logger.info(f"Uploading {file_path.name} ({file_type}) to Google Drive")
        file_id = service.upload_workflow_file(
            file_path=str(file_path),
            workflow_type="drive_test",
            exchange_id="drive-test-run",
            file_type=file_type,
        )

        if file_id:
            logger.info(f"Uploaded {file_path.name} successfully (file_id={file_id})")
        else:
            logger.error(f"Failed to upload {file_path.name}")


def main() -> int:
    drive_config = config.google_drive

    if not drive_config.enabled:
        logger.warning(
            "DRIVE_UPLOAD_ACTIVE is disabled; set it to true to run the upload test."
        )
        return 1

    test_files = _collect_test_files()
    if not test_files:
        logger.error(
            "No PDF/PNG files found under resources/pdf or resources/qr. "
            "Generate a VEP first."
        )
        return 1

    service = GoogleDriveService(
        credentials_path=drive_config.credentials_path,
        token_path=drive_config.token_path,
    )

    if not service.is_available():
        logger.error("Google Drive service is not available. Check credentials/token.")
        return 1

    _upload_files(service, test_files)
    logger.info("Drive upload test completed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
