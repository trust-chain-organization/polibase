"""ProposalParliamentaryGroupJudge repository interface."""

from abc import abstractmethod

from src.domain.entities.proposal_parliamentary_group_judge import (
    ProposalParliamentaryGroupJudge,
)
from src.domain.repositories.base import BaseRepository


class ProposalParliamentaryGroupJudgeRepository(
    BaseRepository[ProposalParliamentaryGroupJudge]
):
    """Repository interface for ProposalParliamentaryGroupJudge entities."""

    @abstractmethod
    async def get_by_proposal(
        self, proposal_id: int
    ) -> list[ProposalParliamentaryGroupJudge]:
        """Get all parliamentary group judges for a specific proposal.

        Args:
            proposal_id: ID of the proposal

        Returns:
            List of ProposalParliamentaryGroupJudge entities
        """
        pass

    @abstractmethod
    async def get_by_parliamentary_group(
        self, parliamentary_group_id: int
    ) -> list[ProposalParliamentaryGroupJudge]:
        """Get all proposal judges for a specific parliamentary group.

        Args:
            parliamentary_group_id: ID of the parliamentary group

        Returns:
            List of ProposalParliamentaryGroupJudge entities
        """
        pass

    @abstractmethod
    async def get_by_proposal_and_group(
        self, proposal_id: int, parliamentary_group_id: int
    ) -> ProposalParliamentaryGroupJudge | None:
        """Get judge for a specific proposal and parliamentary group.

        Args:
            proposal_id: ID of the proposal
            parliamentary_group_id: ID of the parliamentary group

        Returns:
            ProposalParliamentaryGroupJudge entity or None if not found
        """
        pass

    @abstractmethod
    async def bulk_create(
        self, judges: list[ProposalParliamentaryGroupJudge]
    ) -> list[ProposalParliamentaryGroupJudge]:
        """Create multiple parliamentary group judges at once.

        Args:
            judges: List of ProposalParliamentaryGroupJudge entities to create

        Returns:
            List of created ProposalParliamentaryGroupJudge entities with IDs
        """
        pass
