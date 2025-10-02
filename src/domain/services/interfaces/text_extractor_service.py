"""Text extractor service interface definition."""

from typing import Any, Protocol


class ITextExtractorService(Protocol):
    """Interface for text extraction services."""

    async def extract_from_gcs(self, gcs_uri: str) -> str:
        """Extract text content from GCS.

        Args:
            gcs_uri: GCS URI of the text file

        Returns:
            Text content
        """
        ...

    async def parse_speeches(self, text_content: str) -> list[dict[str, Any]]:
        """Parse speeches from text content.

        Args:
            text_content: Text content containing speeches

        Returns:
            List of parsed speeches
        """
        ...
