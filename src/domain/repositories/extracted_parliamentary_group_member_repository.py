"""Repository interface for extracted parliamentary group members."""

from abc import abstractmethod

from src.domain.entities.extracted_parliamentary_group_member import (
    ExtractedParliamentaryGroupMember,
)
from src.domain.repositories.base import BaseRepository


class ExtractedParliamentaryGroupMemberRepository(
    BaseRepository[ExtractedParliamentaryGroupMember]
):
    """Repository interface for extracted parliamentary group members."""

    @abstractmethod
    async def get_pending_members(
        self, parliamentary_group_id: int | None = None
    ) -> list[ExtractedParliamentaryGroupMember]:
        """Get all pending members for matching."""
        pass

    @abstractmethod
    async def get_matched_members(
        self,
        parliamentary_group_id: int | None = None,
        min_confidence: float | None = None,
    ) -> list[ExtractedParliamentaryGroupMember]:
        """Get matched members with optional filtering."""
        pass

    @abstractmethod
    async def update_matching_result(
        self,
        member_id: int,
        politician_id: int | None,
        confidence: float | None,
        status: str,
    ) -> ExtractedParliamentaryGroupMember | None:
        """Update the matching result for a member."""
        pass

    @abstractmethod
    async def get_by_parliamentary_group(
        self, parliamentary_group_id: int
    ) -> list[ExtractedParliamentaryGroupMember]:
        """Get all extracted members for a parliamentary group."""
        pass

    @abstractmethod
    async def get_extraction_summary(
        self, parliamentary_group_id: int | None = None
    ) -> dict[str, int]:
        """Get summary statistics for extracted members."""
        pass

    @abstractmethod
    async def bulk_create(
        self, members: list[ExtractedParliamentaryGroupMember]
    ) -> list[ExtractedParliamentaryGroupMember]:
        """Create multiple extracted members at once."""
        pass
