"""Political party repository interface."""

from abc import abstractmethod

from src.domain.entities.political_party import PoliticalParty
from src.domain.repositories.base import BaseRepository


class PoliticalPartyRepository(BaseRepository[PoliticalParty]):
    """Repository interface for political parties."""

    @abstractmethod
    async def get_by_name(self, name: str) -> PoliticalParty | None:
        """Get political party by name."""
        pass

    @abstractmethod
    async def get_with_members_url(self) -> list[PoliticalParty]:
        """Get political parties that have members list URL."""
        pass

    @abstractmethod
    async def search_by_name(self, name_pattern: str) -> list[PoliticalParty]:
        """Search political parties by name pattern."""
        pass
