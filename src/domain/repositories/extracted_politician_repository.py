"""ExtractedPolitician repository interface."""

from abc import abstractmethod
from datetime import datetime

from src.domain.entities.extracted_politician import ExtractedPolitician
from src.domain.repositories.base import BaseRepository


class ExtractedPoliticianRepository(BaseRepository[ExtractedPolitician]):
    """Repository interface for extracted politicians."""

    @abstractmethod
    async def get_pending(
        self, party_id: int | None = None
    ) -> list[ExtractedPolitician]:
        """Get all pending politicians for review."""
        pass

    @abstractmethod
    async def get_by_status(self, status: str) -> list[ExtractedPolitician]:
        """Get all politicians by status."""
        pass

    @abstractmethod
    async def get_by_party(self, party_id: int) -> list[ExtractedPolitician]:
        """Get all extracted politicians for a party."""
        pass

    @abstractmethod
    async def update_status(
        self,
        politician_id: int,
        status: str,
        reviewer_id: int | None = None,
    ) -> ExtractedPolitician | None:
        """Update the status for a politician."""
        pass

    @abstractmethod
    async def get_summary_by_status(self) -> dict[str, int]:
        """Get summary statistics grouped by status."""
        pass

    @abstractmethod
    async def bulk_create(
        self, politicians: list[ExtractedPolitician]
    ) -> list[ExtractedPolitician]:
        """Create multiple extracted politicians at once."""
        pass

    @abstractmethod
    async def get_duplicates(
        self, name: str, party_id: int | None = None
    ) -> list[ExtractedPolitician]:
        """Find potential duplicate extracted politicians by name and party."""
        pass

    @abstractmethod
    async def get_statistics_by_party(self, party_id: int) -> dict[str, int]:
        """Get statistics for a specific party.

        Returns:
            Dictionary with status counts
            (total, pending, reviewed, approved, rejected, converted)
        """
        pass

    @abstractmethod
    async def get_filtered(
        self,
        statuses: list[str] | None = None,
        party_id: int | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        search_name: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[ExtractedPolitician]:
        """Get filtered politicians with database-level filtering.

        This method performs filtering at the database level for better
        performance with large datasets.

        Args:
            statuses: List of statuses to filter by
            party_id: Party ID to filter by
            start_date: Start date for extraction date filter
            end_date: End date for extraction date filter
            search_name: Name search term (case-insensitive)
            limit: Maximum number of records to return
            offset: Number of records to skip (for pagination)

        Returns:
            List of filtered extracted politicians, sorted by extracted_at desc
        """
        pass
