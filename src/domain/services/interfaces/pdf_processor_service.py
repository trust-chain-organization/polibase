"""PDF processor service interface definition."""

from typing import Any, Protocol


class IPDFProcessorService(Protocol):
    """Interface for PDF processing services."""

    async def process_pdf(self, pdf_url: str) -> list[dict[str, Any]]:
        """Process PDF and extract speeches.

        Args:
            pdf_url: URL or path to the PDF file

        Returns:
            List of extracted speeches with speaker and content
        """
        ...
