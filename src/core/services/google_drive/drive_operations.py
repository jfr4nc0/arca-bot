"""
Google Drive file operations.
Handles upload, download, and file management operations.
"""

import io
import mimetypes
from pathlib import Path
from typing import Any, Dict, List, Optional

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload, MediaIoBaseUpload
from loguru import logger

from core.observability import record_file_operation


class GoogleDriveOperations:
    """Handles Google Drive file operations."""

    def __init__(self, credentials: Credentials):
        """
        Initialize Google Drive operations.

        Args:
            credentials: Valid Google OAuth2 credentials
        """
        self.service = build("drive", "v3", credentials=credentials)

    def upload_file(
        self,
        file_path: str,
        folder_id: Optional[str] = None,
        file_name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        """
        Upload a file to Google Drive.

        Args:
            file_path: Local path to file to upload
            folder_id: Google Drive folder ID (optional)
            file_name: Custom name for uploaded file (optional)
            metadata: Additional file metadata (optional)

        Returns:
            Google Drive file ID if successful, None otherwise
        """
        try:
            file_path_obj = Path(file_path)
            if not file_path_obj.exists():
                logger.error(f"File not found: {file_path}")
                record_file_operation("drive_upload", "failed")
                return None

            # Prepare file metadata
            file_metadata = {
                "name": file_name or file_path_obj.name,
            }

            # Add to folder if specified
            if folder_id:
                file_metadata["parents"] = [folder_id]

            # Add custom metadata if provided
            if metadata:
                file_metadata.update(metadata)

            # Detect MIME type
            mime_type, _ = mimetypes.guess_type(str(file_path_obj))
            if mime_type is None:
                mime_type = "application/octet-stream"

            # Upload file
            media = MediaFileUpload(str(file_path_obj), mimetype=mime_type)

            file = (
                self.service.files()
                .create(
                    body=file_metadata, media_body=media, fields="id,name,size,mimeType"
                )
                .execute()
            )

            file_id = file.get("id")
            logger.info(
                f"File uploaded successfully: {file.get('name')} "
                f"(ID: {file_id}, Size: {file.get('size')} bytes)"
            )

            record_file_operation("drive_upload", "success")
            return file_id

        except HttpError as e:
            logger.error(f"Google Drive API error during upload: {e}")
            record_file_operation("drive_upload", "failed")
            return None
        except Exception as e:
            logger.error(f"Failed to upload file to Google Drive: {e}")
            record_file_operation("drive_upload", "failed")
            return None

    def upload_file_content(
        self,
        content: bytes,
        file_name: str,
        mime_type: str,
        folder_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        """
        Upload file content (bytes) to Google Drive.

        Args:
            content: File content as bytes
            file_name: Name for the uploaded file
            mime_type: MIME type of the file
            folder_id: Google Drive folder ID (optional)
            metadata: Additional file metadata (optional)

        Returns:
            Google Drive file ID if successful, None otherwise
        """
        try:
            # Prepare file metadata
            file_metadata = {"name": file_name}

            # Add to folder if specified
            if folder_id:
                file_metadata["parents"] = [folder_id]

            # Add custom metadata if provided
            if metadata:
                file_metadata.update(metadata)

            # Create media upload from bytes
            media = MediaIoBaseUpload(
                io.BytesIO(content), mimetype=mime_type, resumable=True
            )

            # Upload file
            file = (
                self.service.files()
                .create(body=file_metadata, media_body=media, fields="id,name,size")
                .execute()
            )

            file_id = file.get("id")
            logger.info(
                f"File content uploaded successfully: {file.get('name')} "
                f"(ID: {file_id}, Size: {file.get('size')} bytes)"
            )

            record_file_operation("drive_upload_content", "success")
            return file_id

        except HttpError as e:
            logger.error(f"Google Drive API error during content upload: {e}")
            record_file_operation("drive_upload_content", "failed")
            return None
        except Exception as e:
            logger.error(f"Failed to upload content to Google Drive: {e}")
            record_file_operation("drive_upload_content", "failed")
            return None

    def download_file(self, file_id: str, download_path: str) -> bool:
        """
        Download a file from Google Drive.

        Args:
            file_id: Google Drive file ID
            download_path: Local path to save downloaded file

        Returns:
            True if download successful, False otherwise
        """
        try:
            # Get file metadata first
            file_metadata = self.service.files().get(fileId=file_id).execute()

            # Download file content
            file_content = self.service.files().get_media(fileId=file_id).execute()

            # Save to local path
            download_path_obj = Path(download_path)
            download_path_obj.parent.mkdir(parents=True, exist_ok=True)

            with open(download_path_obj, "wb") as f:
                f.write(file_content)

            logger.info(
                f"File downloaded successfully: {file_metadata.get('name')} "
                f"to {download_path}"
            )

            record_file_operation("drive_download", "success")
            return True

        except HttpError as e:
            logger.error(f"Google Drive API error during download: {e}")
            record_file_operation("drive_download", "failed")
            return False
        except Exception as e:
            logger.error(f"Failed to download file from Google Drive: {e}")
            record_file_operation("drive_download", "failed")
            return False

    def create_folder(
        self, folder_name: str, parent_folder_id: Optional[str] = None
    ) -> Optional[str]:
        """
        Create a folder in Google Drive.

        Args:
            folder_name: Name of the folder to create
            parent_folder_id: Parent folder ID (optional, root if None)

        Returns:
            Folder ID if successful, None otherwise
        """
        try:
            folder_metadata = {
                "name": folder_name,
                "mimeType": "application/vnd.google-apps.folder",
            }

            if parent_folder_id:
                folder_metadata["parents"] = [parent_folder_id]

            folder = (
                self.service.files()
                .create(body=folder_metadata, fields="id,name")
                .execute()
            )

            folder_id = folder.get("id")
            logger.info(f"Folder created successfully: {folder_name} (ID: {folder_id})")

            record_file_operation("drive_create_folder", "success")
            return folder_id

        except HttpError as e:
            logger.error(f"Google Drive API error during folder creation: {e}")
            record_file_operation("drive_create_folder", "failed")
            return None
        except Exception as e:
            logger.error(f"Failed to create folder in Google Drive: {e}")
            record_file_operation("drive_create_folder", "failed")
            return None

    def search_files(
        self,
        query: str,
        max_results: int = 10,
        fields: str = "id,name,mimeType,size,modifiedTime",
    ) -> List[Dict[str, Any]]:
        """
        Search for files in Google Drive.

        Args:
            query: Search query (e.g., "name contains 'VEP'")
            max_results: Maximum number of results to return
            fields: Fields to include in response

        Returns:
            List of file metadata dictionaries
        """
        try:
            results = (
                self.service.files()
                .list(q=query, pageSize=max_results, fields=f"files({fields})")
                .execute()
            )

            files = results.get("files", [])
            logger.info(f"Found {len(files)} files matching query: {query}")

            record_file_operation("drive_search", "success")
            return files

        except HttpError as e:
            logger.error(f"Google Drive API error during search: {e}")
            record_file_operation("drive_search", "failed")
            return []
        except Exception as e:
            logger.error(f"Failed to search files in Google Drive: {e}")
            record_file_operation("drive_search", "failed")
            return []

    def delete_file(self, file_id: str) -> bool:
        """
        Delete a file from Google Drive.

        Args:
            file_id: Google Drive file ID to delete

        Returns:
            True if deletion successful, False otherwise
        """
        try:
            self.service.files().delete(fileId=file_id).execute()
            logger.info(f"File deleted successfully: {file_id}")

            record_file_operation("drive_delete", "success")
            return True

        except HttpError as e:
            logger.error(f"Google Drive API error during deletion: {e}")
            record_file_operation("drive_delete", "failed")
            return False
        except Exception as e:
            logger.error(f"Failed to delete file from Google Drive: {e}")
            record_file_operation("drive_delete", "failed")
            return False

    def get_file_metadata(self, file_id: str) -> Optional[Dict[str, Any]]:
        """
        Get file metadata from Google Drive.

        Args:
            file_id: Google Drive file ID

        Returns:
            File metadata dictionary or None if failed
        """
        try:
            metadata = self.service.files().get(fileId=file_id, fields="*").execute()

            logger.info(f"Retrieved metadata for file: {metadata.get('name')}")
            return metadata

        except HttpError as e:
            logger.error(f"Google Drive API error getting metadata: {e}")
            return None
        except Exception as e:
            logger.error(f"Failed to get file metadata: {e}")
            return None
