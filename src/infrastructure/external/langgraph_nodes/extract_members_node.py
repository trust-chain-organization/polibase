"""LangGraph node for extracting party members from a page."""

import logging
from collections.abc import Awaitable, Callable

from src.domain.services.interfaces.llm_service import ILLMService
from src.domain.services.interfaces.web_scraper_service import IWebScraperService
from src.infrastructure.external.langgraph_state_adapter import (
    LangGraphPartyScrapingStateOptional,
)
from src.party_member_extractor.extractor import PartyMemberExtractor
from src.party_member_extractor.models import WebPageContent

logger = logging.getLogger(__name__)


def create_extract_members_node(
    scraper: IWebScraperService,
    llm_service: ILLMService,
    party_id: int | None = None,
) -> Callable[
    [LangGraphPartyScrapingStateOptional],
    Awaitable[LangGraphPartyScrapingStateOptional],
]:
    """Create a LangGraph node for extracting party members.

    This node:
    1. Fetches HTML content for the current URL
    2. Extracts politician member data using LLM
    3. Adds extracted members to the state

    Args:
        scraper: Web scraper service for fetching HTML
        llm_service: LLM service for extraction
        party_id: Optional party ID for tracking

    Returns:
        Async node function compatible with LangGraph
    """

    async def extract_members_node(
        state: LangGraphPartyScrapingStateOptional,
    ) -> LangGraphPartyScrapingStateOptional:
        """Extract members from the current page.

        This node uses LLM-based extraction to identify politician
        information from member list pages.

        Args:
            state: Current LangGraph state

        Returns:
            Updated state with newly extracted members
        """
        current_url = state.get("current_url", "")
        party_name = state.get("party_name", "")
        extracted_members = state.get("extracted_members", [])

        if not current_url:
            logger.warning("No current URL to extract members from")
            return state

        logger.info(f"Extracting members from: {current_url}")

        try:
            # Fetch HTML content
            html_content = await scraper.fetch_html(current_url)

            if not html_content:
                logger.warning(f"No HTML content fetched from: {current_url}")
                return state

            # Create extractor instance
            extractor = PartyMemberExtractor(
                llm_service=llm_service,
                party_id=party_id,
            )

            # Create WebPageContent
            page = WebPageContent(
                url=current_url,
                html_content=html_content,
                page_number=1,
            )

            # Extract members using the extractor's protected method
            # This is acceptable within our infrastructure layer
            result = extractor._extract_from_single_page(  # type: ignore[reportPrivateUsage]
                page, party_name
            )

            if result is None or not result.members:
                logger.info(f"No members extracted from {current_url}")
                return state

            # Convert members to dict format
            new_members = [
                {
                    "name": member.name,
                    "position": member.position,
                    "electoral_district": member.electoral_district,
                    "prefecture": member.prefecture,
                    "profile_url": member.profile_url,
                    "party_position": member.party_position,
                }
                for member in result.members
            ]

            # Deduplicate by name
            existing_names = {m.get("name") for m in extracted_members}
            unique_new_members = [
                m for m in new_members if m.get("name") not in existing_names
            ]

            # Add to extracted members
            extracted_members.extend(unique_new_members)

            duplicates_count = len(new_members) - len(unique_new_members)
            logger.info(
                f"Extracted {len(new_members)} members from {current_url} "
                f"({len(unique_new_members)} new, {duplicates_count} duplicates)"
            )

            return {
                **state,
                "extracted_members": extracted_members,
            }

        except Exception as e:
            logger.error(
                f"Error extracting members from {current_url}: {e}",
                exc_info=True,
            )
            # Return state unchanged on error (fail gracefully)
            return state

    return extract_members_node
