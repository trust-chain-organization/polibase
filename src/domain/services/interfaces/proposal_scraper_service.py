"""Interface for proposal scraping services."""

from typing import Protocol

from src.domain.types.scraper_types import ScrapedProposal


class IProposalScraperService(Protocol):
    """Interface for scraping proposal information from various sources."""

    async def scrape_proposal(self, url: str) -> ScrapedProposal:
        """Scrape proposal details from a given URL.

        Args:
            url: URL of the proposal page

        Returns:
            ScrapedProposal object containing:
                - content: 議案名/内容
                - proposal_number: 議案番号
                - submission_date: 提出日 (元の日本語形式を保持)
                - summary: 概要（あれば）
                - url: 元のURL

        Raises:
            ValueError: If the URL format is not supported
            RuntimeError: If scraping fails
        """
        ...

    def is_supported_url(self, url: str) -> bool:
        """Check if the given URL is supported by this scraper.

        Args:
            url: URL to check

        Returns:
            True if the URL is supported, False otherwise
        """
        ...
