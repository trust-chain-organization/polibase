"""Storage service interface and implementations."""

from abc import ABC, abstractmethod


class IStorageService(ABC):
    """Interface for storage service."""

    @abstractmethod
    async def upload_file(
        self, file_path: str, content: bytes, content_type: str | None = None
    ) -> str:
        """Upload file and return URI."""
        pass

    @abstractmethod
    async def download_file(self, uri: str) -> bytes:
        """Download file content."""
        pass

    @abstractmethod
    async def exists(self, uri: str) -> bool:
        """Check if file exists."""
        pass

    @abstractmethod
    async def delete_file(self, uri: str) -> bool:
        """Delete file."""
        pass


class GCSStorageService(IStorageService):
    """Google Cloud Storage implementation."""

    def __init__(self, bucket_name: str, credentials_path: str | None = None):
        self.bucket_name = bucket_name
        self.credentials_path = credentials_path
        # Initialize GCS client here

    async def upload_file(
        self, file_path: str, content: bytes, content_type: str | None = None
    ) -> str:
        """Upload file to GCS and return gs:// URI."""
        # Implementation would use GCS client
        # This is a placeholder
        return f"gs://{self.bucket_name}/{file_path}"

    async def download_file(self, uri: str) -> bytes:
        """Download file content from GCS."""
        # Implementation would use GCS client
        # This is a placeholder
        return b"file content"

    async def exists(self, uri: str) -> bool:
        """Check if file exists in GCS."""
        # Implementation would use GCS client
        # This is a placeholder
        return True

    async def delete_file(self, uri: str) -> bool:
        """Delete file from GCS."""
        # Implementation would use GCS client
        # This is a placeholder
        return True


class LocalStorageService(IStorageService):
    """Local filesystem implementation."""

    def __init__(self, base_path: str):
        self.base_path = base_path

    async def upload_file(
        self, file_path: str, content: bytes, content_type: str | None = None
    ) -> str:
        """Save file locally and return file:// URI."""
        from pathlib import Path

        full_path = Path(self.base_path) / file_path
        full_path.parent.mkdir(parents=True, exist_ok=True)

        with open(full_path, "wb") as f:
            f.write(content)

        return f"file://{full_path.absolute()}"

    async def download_file(self, uri: str) -> bytes:
        """Read file content from local filesystem."""
        if uri.startswith("file://"):
            path = uri[7:]  # Remove file:// prefix
        else:
            path = uri

        with open(path, "rb") as f:
            return f.read()

    async def exists(self, uri: str) -> bool:
        """Check if file exists locally."""
        import os

        if uri.startswith("file://"):
            path = uri[7:]
        else:
            path = uri

        return os.path.exists(path)

    async def delete_file(self, uri: str) -> bool:
        """Delete file from local filesystem."""
        import os

        if uri.startswith("file://"):
            path = uri[7:]
        else:
            path = uri

        try:
            os.remove(path)
            return True
        except OSError:
            return False
