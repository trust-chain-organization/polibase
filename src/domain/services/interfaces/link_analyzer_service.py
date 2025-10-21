"""Domain interface for analyzing page links.

This interface provides link analysis capabilities for party scraping workflows
without depending on application layer use cases.
"""

from abc import ABC, abstractmethod


class ILinkAnalyzerService(ABC):
    """Domain interface for analyzing page links."""

    @abstractmethod
    async def analyze_member_list_links(
        self,
        html_content: str,
        current_url: str,
        party_name: str,
        context: str = "",
    ) -> list[str]:
        """Analyze HTML and return high-confidence member list URLs.

        This method examines page links and identifies URLs that likely
        lead to member list pages based on link text, URL patterns,
        and page structure.

        Args:
            html_content: Raw HTML content to analyze
            current_url: URL of the current page
            party_name: Name of the party (for context)
            context: Additional context about the page (optional)

        Returns:
            List of URLs classified as member list pages

        Raises:
            ValueError: If html_content is empty or invalid
        """
        ...
