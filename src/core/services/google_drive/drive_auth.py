"""
Google Drive authentication handler.
Manages OAuth2 credentials and token refresh.
"""

import os
from pathlib import Path
from typing import Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from loguru import logger


class GoogleDriveAuth:
    """Handles Google Drive OAuth2 authentication."""

    def __init__(
        self,
        credentials_path: str,
        token_path: str,
        scopes: list[str] = None,
    ):
        """
        Initialize Google Drive authentication.

        Args:
            credentials_path: Path to Google OAuth2 credentials JSON file
            token_path: Path to store/retrieve user token
            scopes: List of OAuth2 scopes for Drive access
        """
        self.credentials_path = Path(credentials_path)
        self.token_path = Path(token_path)
        self.scopes = scopes or [
            "https://www.googleapis.com/auth/drive.file",
            "https://www.googleapis.com/auth/drive.metadata.readonly",
        ]

    def get_credentials(self) -> Optional[Credentials]:
        """
        Get valid Google credentials for Drive API.

        Returns:
            Valid Credentials object or None if authentication fails
        """
        try:
            creds = None

            # Load existing credentials if available
            if self.token_path.exists():
                logger.info(f"Loading existing credentials from {self.token_path}")
                creds = Credentials.from_authorized_user_file(
                    str(self.token_path), self.scopes
                )

            # Validate and refresh credentials if needed
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    logger.info("Refreshing expired credentials")
                    creds.refresh(Request())
                else:
                    logger.info("Starting OAuth2 flow for new credentials")
                    creds = self._run_oauth_flow()

                # Save credentials for future use
                self._save_credentials(creds)

            logger.info("Google Drive credentials obtained successfully")
            return creds

        except Exception as e:
            logger.error(f"Failed to obtain Google Drive credentials: {e}")
            return None

    def _run_oauth_flow(self) -> Optional[Credentials]:
        """
        Run OAuth2 authorization flow.

        Returns:
            Credentials object from completed flow
        """
        if not self.credentials_path.exists():
            raise FileNotFoundError(
                f"Credentials file not found: {self.credentials_path}. "
                "Please download from Google Cloud Console."
            )

        flow = InstalledAppFlow.from_client_secrets_file(
            str(self.credentials_path), self.scopes
        )

        # Run local server for OAuth2 callback
        creds = flow.run_local_server(port=0)
        logger.info("OAuth2 flow completed successfully")
        return creds

    def _save_credentials(self, creds: Credentials) -> None:
        """
        Save credentials to token file.

        Args:
            creds: Credentials to save
        """
        try:
            # Ensure token directory exists
            self.token_path.parent.mkdir(parents=True, exist_ok=True)

            with open(self.token_path, "w") as token_file:
                token_file.write(creds.to_json())

            logger.info(f"Credentials saved to {self.token_path}")

        except Exception as e:
            logger.error(f"Failed to save credentials: {e}")

    def revoke_credentials(self) -> bool:
        """
        Revoke and delete stored credentials.

        Returns:
            True if credentials were revoked successfully
        """
        try:
            if self.token_path.exists():
                creds = Credentials.from_authorized_user_file(
                    str(self.token_path), self.scopes
                )
                if creds and creds.valid:
                    # Revoke the token
                    creds.revoke(Request())
                    logger.info("Google Drive credentials revoked")

                # Delete the token file
                self.token_path.unlink()
                logger.info(f"Token file deleted: {self.token_path}")

            return True

        except Exception as e:
            logger.error(f"Failed to revoke credentials: {e}")
            return False

    def is_authenticated(self) -> bool:
        """
        Check if user is currently authenticated.

        Returns:
            True if valid credentials exist
        """
        try:
            creds = self.get_credentials()
            return creds is not None and creds.valid
        except Exception:
            return False
