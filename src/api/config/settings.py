"""
Configuration settings management.
"""

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv
from loguru import logger

from core.services.google_drive.drive_service import GoogleDriveService

load_dotenv()


@dataclass
class Settings:
    """Application settings configuration."""

    # Redis configuration
    redis_url: str
    redis_enabled: bool

    # API configuration
    api_title: str
    api_version: str
    api_description: str

    # Environment
    environment: str
    debug: bool

    # Authentication
    api_token: str

    # Security
    allowed_hosts: str

    # Retry configuration
    max_retry_attempts: int

    # Encryption
    fernet_key: str

    # Google Drive configuration
    google_credentials_path: str
    google_token_path: str
    google_drive_enabled: bool

    @classmethod
    def load_from_env(cls) -> "Settings":
        """Load settings from environment variables."""
        api_token = cls._load_api_token()
        return cls(
            redis_url=os.getenv("REDIS_URL", "redis://localhost:6379"),
            redis_enabled=os.getenv("REDIS_ENABLED", "true").lower() == "true",
            api_title="ArcaAutoVep Automatizations API",
            api_version="1.0.0",
            api_description="Automated workflows for ARCA services including CCMA",
            environment=os.getenv("ENVIRONMENT", "development"),
            debug=os.getenv("DEBUG", "false").lower() == "true",
            api_token=api_token,
            allowed_hosts=os.getenv("ALLOWED_HOSTS", "yourdomain.com,*.yourdomain.com"),
            max_retry_attempts=int(os.getenv("MAX_RETRY_ATTEMPTS", "3")),
            fernet_key=os.getenv("FERNET_KEY", ""),
            # Google Drive configuration
            google_credentials_path=os.getenv(
                "GOOGLE_CREDENTIALS_PATH", "secrets/google_credentials.json"
            ),
            google_token_path=os.getenv(
                "GOOGLE_TOKEN_PATH", "secrets/google_token.json"
            ),
            google_drive_enabled=os.getenv("GOOGLE_DRIVE_ENABLED", "false").lower()
            == "true",
        )

    @staticmethod
    def _load_api_token() -> str:
        """Load API token from env var or file path."""
        token = os.getenv("API_AUTH_TOKEN", "")
        if token:
            return token

        token_file = os.getenv("API_AUTH_TOKEN_FILE")
        if token_file:
            try:
                path = Path(token_file)
                if path.exists():
                    token = path.read_text(encoding="utf-8").strip()
                    if token:
                        return token
                    logger.warning("API_AUTH_TOKEN_FILE is empty")
                else:
                    logger.warning(f"API token file not found: {token_file}")
            except Exception as exc:
                logger.error(f"Failed to load API token from file {token_file}: {exc}")

        return ""

    def is_production(self) -> bool:
        """Check if running in production."""
        return self.environment == "production"

    def is_development(self) -> bool:
        """Check if running in development."""
        return self.environment == "development"

    def get_allowed_hosts(self) -> list[str]:
        """Get allowed hosts as a list."""
        return [host.strip() for host in self.allowed_hosts.split(",") if host.strip()]

    def get_google_drive_service(self):
        """Get Google Drive service instance if enabled."""
        if not self.google_drive_enabled:
            return None

        try:
            return GoogleDriveService(
                credentials_path=self.google_credentials_path,
                token_path=self.google_token_path,
            )
        except Exception as e:
            logger.error(f"Failed to initialize Google Drive service: {e}")
            return None


# Global settings instance
settings = Settings.load_from_env()
logger.info(f"Settings loaded for environment: {settings.environment}")
