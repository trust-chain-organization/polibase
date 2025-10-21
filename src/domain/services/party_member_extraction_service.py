"""Domain service for extracting party members from web pages.

This service provides the core business logic for extracting politician
information from HTML content, independent of any specific framework.
"""

from dataclasses import dataclass


@dataclass
class ExtractedMember:
    """Represents an extracted party member."""

    name: str
    position: str | None = None
    electoral_district: str | None = None
    prefecture: str | None = None
    profile_url: str | None = None
    party_position: str | None = None


@dataclass
class MemberExtractionResult:
    """Result of member extraction from a page."""

    members: list[ExtractedMember]
    source_url: str
    extraction_successful: bool
    error_message: str | None = None


class IPartyMemberExtractionService:
    """Domain interface for party member extraction."""

    async def extract_from_html(
        self,
        html_content: str,
        source_url: str,
        party_name: str,
    ) -> MemberExtractionResult:
        """Extract party members from HTML content.

        This method processes HTML content and extracts structured
        politician information using LLM-based analysis.

        Args:
            html_content: Raw HTML content to analyze
            source_url: URL where the content was fetched from
            party_name: Name of the political party

        Returns:
            MemberExtractionResult containing extracted members and metadata

        Raises:
            ValueError: If html_content or party_name is empty
        """
        raise NotImplementedError
