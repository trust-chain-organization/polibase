"""Web scraper service interface definition."""

from typing import Any, Protocol


class IWebScraperService(Protocol):
    """Interface for web scraping services."""

    def is_supported_url(self, url: str) -> bool:
        """Check if the URL is supported for scraping.

        Args:
            url: URL to check

        Returns:
            True if the URL is supported, False otherwise
        """
        ...

    async def scrape_party_members(
        self, url: str, party_id: int
    ) -> list[dict[str, Any]]:
        """Scrape party member information from website.

        Args:
            url: URL of the party members page
            party_id: ID of the political party

        Returns:
            List of scraped member information
        """
        ...

    async def scrape_conference_members(self, url: str) -> list[dict[str, Any]]:
        """Scrape conference member information from website.

        Args:
            url: URL of the conference members page

        Returns:
            List of scraped member information
        """
        ...

    async def scrape_meeting_minutes(self, url: str) -> dict[str, Any]:
        """Scrape meeting minutes from website.

        Args:
            url: URL of the meeting minutes page

        Returns:
            Scraped meeting minutes data
        """
        ...

    async def scrape_proposal_judges(self, url: str) -> list[dict[str, Any]]:
        """Scrape proposal voting information from website.

        Args:
            url: URL of the proposal voting results page

        Returns:
            List of voting information with name, party, and judgment
        """
        ...
