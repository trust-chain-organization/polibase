"""Web scraper service interface and implementation."""

from abc import ABC, abstractmethod
from typing import Any


class IWebScraperService(ABC):
    """Interface for web scraping service."""

    @abstractmethod
    async def scrape_party_members(
        self, url: str, party_id: int, party_name: str | None = None
    ) -> list[dict[str, Any]]:
        """Scrape party members from website."""
        pass

    @abstractmethod
    async def scrape_conference_members(self, url: str) -> list[dict[str, Any]]:
        """Scrape conference members from website."""
        pass

    @abstractmethod
    async def scrape_meeting_minutes(
        self, url: str, upload_to_gcs: bool = False
    ) -> dict[str, Any]:
        """Scrape meeting minutes from website."""
        pass


class PlaywrightScraperService(IWebScraperService):
    """Playwright-based implementation of web scraper."""

    def __init__(self, headless: bool = True):
        self.headless = headless
        # Initialize Playwright here

    async def scrape_party_members(
        self, url: str, party_id: int, party_name: str | None = None
    ) -> list[dict[str, Any]]:
        """Scrape party members using Playwright with actual implementation."""
        from src.party_member_extractor.extractor import PartyMemberExtractor
        from src.party_member_extractor.html_fetcher import PartyMemberPageFetcher

        # Get party name if not provided
        if party_name is None:
            # Try to get party name from database
            from sqlalchemy.orm import sessionmaker

            from src.config.database import get_db_engine
            from src.infrastructure.persistence.async_session_adapter import (
                AsyncSessionAdapter,
            )
            from src.infrastructure.persistence.political_party_repository_impl import (
                PoliticalPartyRepositoryImpl,
            )

            engine = get_db_engine()
            session_local = sessionmaker(bind=engine)
            session = session_local()
            async_session = AsyncSessionAdapter(session)
            party_repo = PoliticalPartyRepositoryImpl(async_session)

            try:
                party = await party_repo.get_by_id(party_id)
                if party:
                    party_name = party.name
                else:
                    party_name = "Unknown Party"
            finally:
                session.close()

        try:
            # Fetch pages with JavaScript rendering support
            async with PartyMemberPageFetcher() as fetcher:
                pages = await fetcher.fetch_all_pages(url, max_pages=10)

                if not pages:
                    import logging

                    logger = logging.getLogger(__name__)
                    logger.warning(f"No pages fetched from {url}")
                    return []

                # Extract party members using LLM
                extractor = PartyMemberExtractor(party_id=party_id)
                members_list = await extractor.extract_from_pages(pages, party_name)

                # Convert to expected format
                result = []
                if members_list and members_list.members:
                    for member in members_list.members:
                        result.append(
                            {
                                "name": member.name,
                                "furigana": member.furigana,
                                "position": member.position,
                                "district": member.electoral_district,
                                "profile_image_url": member.profile_image_url,
                                "profile_page_url": member.profile_page_url,
                            }
                        )

                return result

        except Exception as e:
            import logging

            logger = logging.getLogger(__name__)
            logger.error(f"Failed to scrape party members from {url}: {e}")
            # Return empty list on error instead of dummy data
            return []

    async def scrape_conference_members(self, url: str) -> list[dict[str, Any]]:
        """Scrape conference members using Playwright."""
        # Implementation would use Playwright to navigate and extract data
        # This is a placeholder
        return [
            {
                "name": "佐藤花子",
                "party": "○○党",
                "role": "議長",
                "profile_url": "https://example.com/member/1",
            }
        ]

    async def scrape_meeting_minutes(
        self, url: str, upload_to_gcs: bool = False
    ) -> dict[str, Any]:
        """Scrape meeting minutes using Playwright."""
        # Implementation would use Playwright to navigate and extract data
        # This is a placeholder
        return {
            "meeting_date": "2024-01-15",
            "meeting_name": "本会議",
            "pdf_url": "https://example.com/minutes.pdf",
            "text_content": "会議の内容...",
            "gcs_pdf_uri": "gs://bucket/minutes.pdf" if upload_to_gcs else None,
            "gcs_text_uri": "gs://bucket/minutes.txt" if upload_to_gcs else None,
        }
