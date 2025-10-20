"""Interface for HTML link extraction service."""

from abc import ABC, abstractmethod

from src.domain.value_objects.link import Link


class IHtmlLinkExtractorService(ABC):
    """Interface for extracting links from HTML content.

    This interface defines the contract for services that extract links
    from HTML content. Implementations should handle HTML parsing and
    link extraction without containing business logic about which links
    to keep or how to classify them.
    """

    @abstractmethod
    def extract_links(self, html_content: str, base_url: str) -> list[Link]:
        """Extract all links from HTML content.

        Args:
            html_content: Raw HTML content to parse
            base_url: Base URL for resolving relative links

        Returns:
            List of Link value objects with absolute URLs

        Raises:
            ValueError: If html_content is empty or base_url is invalid
        """
        pass
