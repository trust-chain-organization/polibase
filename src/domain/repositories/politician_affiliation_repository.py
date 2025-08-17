"""Repository interface for politician affiliations."""

from abc import abstractmethod
from datetime import date

from src.domain.entities.politician_affiliation import PoliticianAffiliation
from src.domain.repositories.base import BaseRepository


class PoliticianAffiliationRepository(BaseRepository[PoliticianAffiliation]):
    """Repository interface for politician affiliations."""

    @abstractmethod
    async def get_by_politician_and_conference(
        self, politician_id: int, conference_id: int, active_only: bool = True
    ) -> list[PoliticianAffiliation]:
        """Get affiliations by politician and conference."""
        pass

    @abstractmethod
    async def get_by_conference(
        self, conference_id: int, active_only: bool = True
    ) -> list[PoliticianAffiliation]:
        """Get all affiliations for a conference."""
        pass

    @abstractmethod
    async def get_by_politician(
        self, politician_id: int, active_only: bool = True
    ) -> list[PoliticianAffiliation]:
        """Get all affiliations for a politician."""
        pass

    @abstractmethod
    async def upsert(
        self,
        politician_id: int,
        conference_id: int,
        start_date: date,
        end_date: date | None = None,
        role: str | None = None,
    ) -> PoliticianAffiliation:
        """Create or update an affiliation."""
        pass

    @abstractmethod
    async def end_affiliation(
        self, affiliation_id: int, end_date: date
    ) -> PoliticianAffiliation | None:
        """End an affiliation by setting the end date."""
        pass
