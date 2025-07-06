"""LLM service interface definition."""

from typing import Any, Protocol


class ILLMService(Protocol):
    """Interface for LLM services."""

    async def match_speaker_to_politician(
        self, context: dict[str, Any]
    ) -> dict[str, Any] | None:
        """Match a speaker to a politician using LLM.

        Args:
            context: Context containing speaker info and candidate politicians

        Returns:
            Matching result with politician_id and confidence score
        """
        ...

    async def extract_speeches_from_text(self, text: str) -> list[dict[str, str]]:
        """Extract speeches from meeting minutes text.

        Args:
            text: Meeting minutes text content

        Returns:
            List of speeches with speaker and content
        """
        ...

    async def extract_party_members(
        self, html_content: str, party_id: int
    ) -> list[dict[str, Any]]:
        """Extract party member information from HTML.

        Args:
            html_content: HTML content of party members page
            party_id: ID of the political party

        Returns:
            List of extracted member information
        """
        ...

    async def match_conference_member(
        self, member_name: str, party_name: str | None, candidates: list[dict[str, Any]]
    ) -> dict[str, Any] | None:
        """Match a conference member to a politician.

        Args:
            member_name: Name of the conference member
            party_name: Party affiliation if known
            candidates: List of candidate politicians

        Returns:
            Matching result with politician_id and confidence score
        """
        ...
