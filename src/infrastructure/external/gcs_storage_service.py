"""GCS storage service implementation."""

from src.domain.services.interfaces.storage_service import IStorageService
from src.utils.gcs_storage import GCSStorage


class GCSStorageService(IStorageService):
    """GCS implementation of storage service."""

    def __init__(self, bucket_name: str, project_id: str | None = None):
        """Initialize GCS storage service.

        Args:
            bucket_name: GCS bucket name
            project_id: GCP project ID (optional)
        """
        self._gcs = GCSStorage(bucket_name=bucket_name, project_id=project_id)

    def download_content(self, uri: str) -> str:
        """Download content from GCS.

        Args:
            uri: GCS URI (e.g., gs://bucket/path/to/file)

        Returns:
            Content as string
        """
        content = self._gcs.download_content(uri)
        if content is None:
            raise ValueError(f"Failed to download content from {uri}")
        return content

    def upload_content(self, content: str, destination_uri: str) -> str:
        """Upload content to GCS.

        Args:
            content: Content to upload
            destination_uri: Destination URI

        Returns:
            URI of uploaded content
        """
        return self._gcs.upload_content(content, destination_uri)
