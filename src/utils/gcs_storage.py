"""Google Cloud Storage utility for uploading scraped minutes data."""
import os
from typing import Optional, Union
from pathlib import Path
import logging
from google.cloud import storage
from google.cloud.exceptions import GoogleCloudError

logger = logging.getLogger(__name__)


class GCSStorage:
    """Handle Google Cloud Storage operations for scraped minutes."""

    def __init__(self, bucket_name: str, project_id: Optional[str] = None):
        """Initialize GCS storage client.
        
        Args:
            bucket_name: GCS bucket name
            project_id: GCP project ID (optional, uses default if not provided)
        """
        self.bucket_name = bucket_name
        try:
            if project_id:
                self.client = storage.Client(project=project_id)
            else:
                self.client = storage.Client()
            self.bucket = self.client.bucket(bucket_name)
        except Exception as e:
            logger.error(f"Failed to initialize GCS client: {e}")
            raise

    def upload_file(
        self, 
        local_path: Union[str, Path], 
        gcs_path: str,
        content_type: Optional[str] = None
    ) -> str:
        """Upload a file to GCS.
        
        Args:
            local_path: Local file path to upload
            gcs_path: Destination path in GCS (without bucket name)
            content_type: MIME type of the file (auto-detected if not provided)
            
        Returns:
            Public URL of the uploaded file
        """
        local_path = Path(local_path)
        
        if not local_path.exists():
            raise FileNotFoundError(f"Local file not found: {local_path}")
            
        try:
            blob = self.bucket.blob(gcs_path)
            
            # Auto-detect content type if not provided
            if not content_type:
                if local_path.suffix == '.pdf':
                    content_type = 'application/pdf'
                elif local_path.suffix == '.json':
                    content_type = 'application/json'
                elif local_path.suffix == '.txt':
                    content_type = 'text/plain'
                    
            blob.upload_from_filename(str(local_path), content_type=content_type)
            logger.info(f"Uploaded {local_path} to gs://{self.bucket_name}/{gcs_path}")
            
            return f"gs://{self.bucket_name}/{gcs_path}"
            
        except GoogleCloudError as e:
            logger.error(f"GCS upload failed: {e}")
            raise
            
    def upload_content(
        self, 
        content: Union[str, bytes], 
        gcs_path: str,
        content_type: Optional[str] = None
    ) -> str:
        """Upload content directly to GCS without saving to disk.
        
        Args:
            content: Content to upload (string or bytes)
            gcs_path: Destination path in GCS (without bucket name)
            content_type: MIME type of the content
            
        Returns:
            Public URL of the uploaded file
        """
        try:
            blob = self.bucket.blob(gcs_path)
            
            if isinstance(content, str):
                content = content.encode('utf-8')
                if not content_type:
                    content_type = 'text/plain; charset=utf-8'
                    
            blob.upload_from_string(content, content_type=content_type)
            logger.info(f"Uploaded content to gs://{self.bucket_name}/{gcs_path}")
            
            return f"gs://{self.bucket_name}/{gcs_path}"
            
        except GoogleCloudError as e:
            logger.error(f"GCS upload failed: {e}")
            raise
            
    def download_file(self, gcs_path: str, local_path: Union[str, Path]) -> None:
        """Download a file from GCS.
        
        Args:
            gcs_path: Source path in GCS (without bucket name)
            local_path: Local destination path
        """
        local_path = Path(local_path)
        local_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            blob = self.bucket.blob(gcs_path)
            blob.download_to_filename(str(local_path))
            logger.info(f"Downloaded gs://{self.bucket_name}/{gcs_path} to {local_path}")
        except GoogleCloudError as e:
            logger.error(f"GCS download failed: {e}")
            raise
            
    def exists(self, gcs_path: str) -> bool:
        """Check if a file exists in GCS.
        
        Args:
            gcs_path: Path in GCS (without bucket name)
            
        Returns:
            True if file exists, False otherwise
        """
        try:
            blob = self.bucket.blob(gcs_path)
            return blob.exists()
        except GoogleCloudError as e:
            logger.error(f"GCS exists check failed: {e}")
            return False
            
    def list_files(self, prefix: str = "") -> list[str]:
        """List files in GCS bucket with optional prefix.
        
        Args:
            prefix: Path prefix to filter files
            
        Returns:
            List of file paths in the bucket
        """
        try:
            blobs = self.bucket.list_blobs(prefix=prefix)
            return [blob.name for blob in blobs]
        except GoogleCloudError as e:
            logger.error(f"GCS list files failed: {e}")
            return []