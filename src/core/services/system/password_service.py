"""
Password service for retrieving ARCA credentials from encrypted Excel file.
"""

import io
from pathlib import Path
from typing import Dict, Optional

import pandas as pd
from loguru import logger

from core.exceptions.password_exceptions import (
    PasswordDecryptionError,
    PasswordFileError,
    PasswordNotFoundError,
)
from core.services.system.file_handler import FileHandler


class PasswordService:
    """Service for retrieving passwords from encrypted Excel file using pandas."""

    def __init__(
        self, fernet_key: str, excel_file_path: str = "./resources/claves/claves.xlsx"
    ):
        """
        Initialize password service.

        Args:
            fernet_key: Fernet encryption key for decrypting the Excel file
            excel_file_path: Path to the encrypted Excel file
        """
        self.fernet_key = fernet_key
        self.excel_file_path = Path(excel_file_path)
        self.file_handler = FileHandler()
        self._password_cache: Optional[Dict[str, str]] = None
        logger.info(
            f"PasswordService initialized with Excel file: {self.excel_file_path}"
        )

    def _load_passwords(self) -> Dict[str, str]:
        """
        Load and decrypt passwords from Excel file using pandas.

        Returns:
            Dictionary mapping CUIT to password

        Raises:
            PasswordDecryptionError: If file cannot be decrypted
            PasswordFileError: If file cannot be parsed or has invalid structure
        """
        try:
            logger.info("Loading passwords from encrypted Excel file")

            # Decrypt the Excel file
            try:
                decrypted_content = self.file_handler.decrypt_file(
                    self.excel_file_path, self.fernet_key
                )
            except Exception as e:
                logger.error(f"Failed to decrypt password file: {e}")
                raise PasswordDecryptionError(details={"original_error": str(e)})

            # Read Excel content from decrypted bytes using pandas
            excel_data = io.BytesIO(decrypted_content)
            df = pd.read_excel(excel_data, engine="openpyxl")

            logger.info(f"Excel file loaded with columns: {list(df.columns)}")
            logger.info(f"Excel file has {len(df)} rows")

            # Use specific column names based on actual Excel structure
            cuit_col = "cuit"
            password_col = "clave"

            if cuit_col not in df.columns:
                raise PasswordFileError(
                    f"CUIT column '{cuit_col}' not found. Available columns: {list(df.columns)}",
                    details={"available_columns": list(df.columns)},
                )
            if password_col not in df.columns:
                raise PasswordFileError(
                    f"Password column '{password_col}' not found. Available columns: {list(df.columns)}",
                    details={"available_columns": list(df.columns)},
                )

            logger.info(
                f"Using CUIT column: '{cuit_col}', Password column: '{password_col}'"
            )

            # Build CUIT -> password mapping using pandas operations
            # Filter out NaN values and convert to string
            df_clean = df[[cuit_col, password_col]].dropna()
            df_clean[cuit_col] = df_clean[cuit_col].astype(str).str.strip()
            df_clean[password_col] = df_clean[password_col].astype(str).str.strip()

            # Remove empty strings and 'nan' values
            df_clean = df_clean[
                (df_clean[cuit_col] != "")
                & (df_clean[cuit_col] != "nan")
                & (df_clean[password_col] != "")
                & (df_clean[password_col] != "nan")
            ]

            # Convert to dictionary
            password_map = df_clean.set_index(cuit_col)[password_col].to_dict()

            logger.info(f"Loaded {len(password_map)} password entries from Excel file")
            logger.debug(
                f"Available CUITs: {list(password_map.keys())[:5]}..."
            )  # Show first 5 for debugging

            return password_map

        except (PasswordDecryptionError, PasswordFileError):
            # Re-raise our custom exceptions as-is
            raise
        except Exception as e:
            logger.error(f"Unexpected error loading passwords from Excel file: {e}")
            raise PasswordFileError(
                f"Unexpected error: {str(e)}",
                details={"original_error": str(e), "error_type": type(e).__name__},
            )

    def get_password(self, cuit: str) -> str:
        """
        Get password for a given CUIT.

        Args:
            cuit: CUIT number to lookup

        Returns:
            Password for the CUIT

        Raises:
            PasswordNotFoundError: If CUIT is not found in the password file
        """
        # Load passwords if not cached
        if self._password_cache is None:
            self._password_cache = self._load_passwords()

        # Clean and normalize CUIT for lookup
        clean_cuit = str(cuit).strip()

        if clean_cuit in self._password_cache:
            logger.debug(f"Password found for CUIT: {clean_cuit}")
            return self._password_cache[clean_cuit]
        else:
            logger.warning(f"Password not found for CUIT: {clean_cuit}")
            logger.debug(
                f"Available CUITs in cache: {list(self._password_cache.keys())[:10]}..."
            )
            raise PasswordNotFoundError(clean_cuit)

    def reload_passwords(self) -> None:
        """
        Force reload passwords from Excel file.
        Useful if the Excel file has been updated.
        """
        logger.info("Reloading passwords from Excel file")
        self._password_cache = None
        self._password_cache = self._load_passwords()

    def clear_cache(self) -> None:
        """Clear password cache from memory."""
        logger.info("Clearing password cache")
        self._password_cache = None

    def has_password(self, cuit: str) -> bool:
        """
        Check if password exists for a given CUIT without raising exception.

        Args:
            cuit: CUIT number to check

        Returns:
            True if password exists, False otherwise
        """
        try:
            self.get_password(cuit)
            return True
        except PasswordNotFoundError:
            return False

    def get_stats(self) -> Dict[str, int]:
        """
        Get statistics about loaded passwords.

        Returns:
            Dictionary with password cache statistics
        """
        if self._password_cache is None:
            self._password_cache = self._load_passwords()

        return {
            "total_passwords": len(self._password_cache),
            "cache_loaded": self._password_cache is not None,
        }
