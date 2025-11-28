import os
from typing import Optional

from dotenv import load_dotenv
from pydantic import BaseModel

load_dotenv(override=True)


class ARCAConfig(BaseModel):
    base_url: str = os.getenv("ARCA_BASE_URL", "https://www.afip.gob.ar")
    login_url: str = os.getenv(
        "ARCA_LOGIN_URL", "https://auth.afip.gob.ar/contribuyente_/login.xhtml"
    )

    # Browser settings
    headless: bool = False
    implicit_wait: int = 3  # Optimized for faster operations
    page_load_timeout: int = 15  # Optimized page load timeout

    # Credentials from environment
    # Note: CUIT is used as the username in AFIP login
    cuit: Optional[str] = os.getenv("AFIP_CUIT")
    password: Optional[str] = os.getenv("AFIP_PASSWORD")


class GoogleDriveConfig(BaseModel):
    enabled: bool = os.getenv("DRIVE_UPLOAD_ACTIVE", "false").lower() == "true"
    credentials_path: str = os.getenv(
        "GOOGLE_CREDENTIALS_PATH", "secrets/google_credentials.json"
    )
    token_path: str = os.getenv("GOOGLE_TOKEN_PATH", "secrets/google_token.json")


class AppConfig(BaseModel):
    arca: ARCAConfig = ARCAConfig()
    google_drive: GoogleDriveConfig = GoogleDriveConfig()
    log_level: str = "INFO"
    output_dir: str = "output"


config = AppConfig()
