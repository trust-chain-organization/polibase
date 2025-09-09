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

    @abstractmethod
    async def get_by_meeting_id(self, meeting_id: int) -> list[Proposal]:
        """Get proposals by meeting ID.

        Args:
            meeting_id: Meeting ID to filter by

        Returns:
            List of proposals associated with the specified meeting
        """
        pass

    @abstractmethod
    async def get_by_proposal_number(self, proposal_number: str) -> Proposal | None:
        """Get proposal by proposal number.

        Args:
            proposal_number: Proposal number (e.g., "議案第1号")

        Returns:
            Proposal if found, None otherwise
        """
        pass

    @abstractmethod
    async def get_by_submission_date_range(
        self, start_date: str, end_date: str
    ) -> list[Proposal]:
        """Get proposals submitted within a date range.

        Args:
            start_date: Start date in ISO format (YYYY-MM-DD)
            end_date: End date in ISO format (YYYY-MM-DD)

        Returns:
            List of proposals submitted within the date range
        """
        pass
