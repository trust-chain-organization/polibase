"""ExtractedPolitician repository interface."""

from abc import abstractmethod

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
