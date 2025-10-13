"""Storage service interface."""

from typing import Protocol


class IStorageService(Protocol):
    """Interface for storage services (GCS, S3, etc.)."""

    async def download_file(self, uri: str) -> bytes:
        """Download file from storage.

        Args:
            uri: Storage URI (e.g., gs://bucket/path/to/file)

        Returns:
            Content as bytes

        Raises:
            StorageError: If download fails
        """
        ...

    async def upload_file(
        self, file_path: str, content: bytes, content_type: str | None = None
    ) -> str:
        """Upload file to storage.

        Args:
            file_path: Destination path in storage
            content: Content to upload as bytes
            content_type: Optional content type

        Returns:
            URI of uploaded content

        Raises:
            StorageError: If upload fails
        """
        ...

    async def exists(self, uri: str) -> bool:
        """Check if file exists in storage.

        Args:
            uri: Storage URI

        Returns:
            True if file exists, False otherwise
        """
        ...

    async def delete_file(self, uri: str) -> bool:
        """Delete file from storage.

        Args:
            uri: Storage URI

        Returns:
            True if deletion was successful

        Raises:
            StorageError: If deletion fails
        """
        ...
