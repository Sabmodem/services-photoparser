from abc import ABC, abstractmethod
from io import BytesIO
from typing import Protocol


class FileStorageInterface(ABC):
    """Interface for file storage backends (S3, local, GCS, etc.)."""

    @abstractmethod
    async def upload_file(self, storage_path: str, file_data) -> str:
        """Upload file data and return the storage path."""
        ...

    @abstractmethod
    async def download_file(self, storage_path: str):
        """Download file and return file data."""
        ...

    @abstractmethod
    async def delete_file(self, storage_path: str) -> bool:
        """Delete a file. Returns True if deleted, False if not found."""
        ...

    @abstractmethod
    async def get_file_url(self, storage_path: str, expires_in: int = 3600) -> str:
        """Get a public/signed URL for the file."""
        ...

    @abstractmethod
    async def get_upload_url(self, storage_path: str, expires_in: int = 3600) -> str:
        """Get a presigned upload URL."""
        ...

    @abstractmethod
    async def file_exists(self, storage_path: str) -> bool:
        """Check if a file exists."""
        ...
