"""
File data response models - handling file serialization.
"""

from pydantic import BaseModel, Field


class FileData(BaseModel):
    """Model for file data with base64 encoding."""

    filename: str = Field(..., description="Name of the file")
    content_type: str = Field(..., description="MIME type of the file")
    data: str = Field(..., description="Base64 encoded file content")

    class Config:
        json_schema_extra = {
            "example": {
                "filename": "vep_20250115_123456.pdf",
                "content_type": "application/pdf",
                "data": "JVBERi0xLjQKJeLjz9MKMSAwIG9iago8PAovVHlwZSAvQ2F0YWxvZwov...",
            }
        }
