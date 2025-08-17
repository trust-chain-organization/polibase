"""Repository interface for extracted conference members."""

from abc import abstractmethod

from src.domain.entities.extracted_conference_member import ExtractedConferenceMember
from src.domain.repositories.base import BaseRepository


class ExtractedConferenceMemberRepository(BaseRepository[ExtractedConferenceMember]):
    """Repository interface for extracted conference members."""

    @abstractmethod
    async def get_pending_members(
        self, conference_id: int | None = None
    ) -> list[ExtractedConferenceMember]:
        """Get all pending members for matching."""
        pass

    @abstractmethod
    async def get_matched_members(
        self, conference_id: int | None = None, min_confidence: float | None = None
    ) -> list[ExtractedConferenceMember]:
        """Get matched members with optional filtering."""
        pass

    @abstractmethod
    async def update_matching_result(
        self,
        member_id: int,
        politician_id: int | None,
        confidence: float | None,
        status: str,
    ) -> ExtractedConferenceMember | None:
        """Update the matching result for a member."""
        pass

    @abstractmethod
    async def get_by_conference(
        self, conference_id: int
    ) -> list[ExtractedConferenceMember]:
        """Get all extracted members for a conference."""
        pass

    @abstractmethod
    async def get_extraction_summary(
        self, conference_id: int | None = None
    ) -> dict[str, int]:
        """Get summary statistics for extracted members."""
        pass

    @abstractmethod
    async def bulk_create(
        self, members: list[ExtractedConferenceMember]
    ) -> list[ExtractedConferenceMember]:
        """Create multiple extracted members at once."""
        pass
