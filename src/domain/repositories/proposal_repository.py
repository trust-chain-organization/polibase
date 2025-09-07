"""Proposal repository interface."""

from abc import abstractmethod

from src.domain.entities.proposal import Proposal
from src.domain.repositories.base import BaseRepository


class ProposalRepository(BaseRepository[Proposal]):
    """Proposal repository interface."""

    @abstractmethod
    async def get_by_status(self, status: str) -> list[Proposal]:
        """Get proposals by status.

        Args:
            status: Status to filter by (e.g., "審議中", "可決", "否決")

        Returns:
            List of proposals with the specified status
        """
        pass
