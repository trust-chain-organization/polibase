"""Storage service interface."""

from typing import Protocol


class IStorageService(Protocol):
    """Interface for storage services (GCS, S3, etc.)."""

    def download_content(self, uri: str) -> str:
        """Download content from storage.

        Args:
            uri: Storage URI (e.g., gs://bucket/path/to/file)

        Returns:
            Content as string

        Raises:
            StorageError: If download fails
        """
        ...

    def upload_content(self, content: str, destination_uri: str) -> str:
        """Upload content to storage.

        Args:
            content: Content to upload
            destination_uri: Destination URI

        Returns:
            URI of uploaded content

        Raises:
            StorageError: If upload fails
        """
        ...
