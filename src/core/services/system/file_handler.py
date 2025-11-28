"""
File handler that consolidates all file management operations.
"""

import shutil
import time
from pathlib import Path
from typing import Optional, Set

from cryptography.fernet import Fernet
from loguru import logger


class FileHandler:
    """Unified file handler for all file operations."""

    def __init__(self):
        pass

    def get_files_snapshot(self, directory: Path, pattern: str) -> Set[Path]:
        """
        Get snapshot of files matching pattern in directory.

        Args:
            directory: Directory to scan
            pattern: File pattern to match (e.g., "*.pdf")

        Returns:
            Set of matching file paths
        """
        try:
            if not directory.exists():
                logger.warning(f"Directory does not exist: {directory}")
                return set()

            return set(directory.glob(pattern))
        except Exception as e:
            logger.error(f"Error getting files snapshot: {e}")
            return set()

    def wait_for_new_file(
        self, initial_files: Set[Path], directory: Path, pattern: str, timeout: int = 30
    ) -> Optional[Path]:
        """
        Wait for a new file to appear in directory.

        Args:
            initial_files: Set of files that existed before
            directory: Directory to monitor
            pattern: File pattern to match
            timeout: Maximum wait time in seconds

        Returns:
            Path to new file, or None if timeout
        """
        logger.info(f"Waiting for new {pattern} file in {directory}")
        wait_interval = 0.5  # Check more frequently
        elapsed_time = 0

        while elapsed_time < timeout:
            time.sleep(wait_interval)
            elapsed_time += wait_interval

            # Check for new files
            current_files = self.get_files_snapshot(directory, pattern)
            new_files = current_files - initial_files

            if new_files:
                new_file = list(new_files)[0]  # Get the first new file
                logger.info(f"New file detected: {new_file.name}")
                return new_file

            # Check for incomplete downloads
            if pattern == "*.pdf":
                crdownload_files = list(directory.glob("*.crdownload"))
                if crdownload_files:
                    logger.info("Download in progress (found .crdownload file)")
                    continue

        logger.warning(f"File wait timeout after {timeout} seconds")
        return None

    def move_file(self, source: Path, destination: Path) -> bool:
        """
        Move file from source to destination.

        Args:
            source: Source file path
            destination: Destination file path

        Returns:
            True if file was moved successfully
        """
        try:
            # Ensure destination directory exists
            destination.parent.mkdir(parents=True, exist_ok=True)

            shutil.move(str(source), str(destination))
            logger.info(f"File moved: {source} -> {destination}")
            return True
        except Exception as e:
            logger.error(f"Error moving file {source} to {destination}: {e}")
            return False

    def ensure_directory(self, directory: Path) -> bool:
        """
        Ensure directory exists.

        Args:
            directory: Directory path to create

        Returns:
            True if directory exists or was created
        """
        try:
            directory.mkdir(parents=True, exist_ok=True)
            return True
        except Exception as e:
            logger.error(f"Error creating directory {directory}: {e}")
            return False

    def save_text_file(self, content: str, filepath: Path) -> bool:
        """
        Save text content to a file.

        Args:
            content: Text content to save
            filepath: Path to save file

        Returns:
            True if file was saved successfully
        """
        try:
            # Ensure parent directory exists
            filepath.parent.mkdir(parents=True, exist_ok=True)

            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)

            logger.info(f"Text file saved: {filepath}")
            return True
        except Exception as e:
            logger.error(f"Error saving text file {filepath}: {e}")
            return False

    def save_binary_file(self, data: bytes, filepath: Path) -> bool:
        """
        Save binary data to a file.

        Args:
            data: Binary data to save
            filepath: Path to save file

        Returns:
            True if file was saved successfully
        """
        try:
            # Ensure parent directory exists
            filepath.parent.mkdir(parents=True, exist_ok=True)

            with open(filepath, "wb") as f:
                f.write(data)

            logger.info(f"Binary file saved: {filepath}")
            return True
        except Exception as e:
            logger.error(f"Error saving binary file {filepath}: {e}")
            return False

    def decrypt_file(self, file_path: Path, key: str) -> bytes:
        """
        Decrypt a file using Fernet symmetric encryption.

        Args:
            file_path: Path to file to decrypt
            key: Fernet key to use for decryption

        Returns:
            Decrypted content as bytes
        """
        try:
            # Initialize the Fernet object
            fernet = Fernet(key)

            # Read the encrypted content
            with open(file_path, "rb") as encrypted_file:
                encrypted_content = encrypted_file.read()

            # Decrypt the content using Fernet
            decrypted_content = fernet.decrypt(encrypted_content)

            logger.info(f"File decrypted successfully: {file_path}")
            return decrypted_content

        except Exception as e:
            logger.error(f"Error decrypting file {file_path}: {e}")
            raise e
