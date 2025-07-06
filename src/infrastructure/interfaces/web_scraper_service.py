"""Web scraper service interface definition."""

from typing import Any, Protocol


class IWebScraperService(Protocol):
    """Interface for web scraping services."""

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
