"""Politician repository interface."""

from abc import abstractmethod

from src.domain.entities.politician import Politician
from src.domain.repositories.base import BaseRepository


class PoliticianRepository(BaseRepository[Politician]):
    """Repository interface for politicians."""

    @abstractmethod
    async def get_by_name_and_party(
        self, name: str, political_party_id: int | None = None
    ) -> Politician | None:
        """Get politician by name and political party."""
        pass

    @abstractmethod
    async def get_by_speaker_id(self, speaker_id: int) -> Politician | None:
        """Get politician by speaker ID."""
        pass

    @abstractmethod
    async def get_by_party(self, political_party_id: int) -> list[Politician]:
        """Get all politicians for a political party."""
        pass

    @abstractmethod
    async def search_by_name(self, name_pattern: str) -> list[Politician]:
        """Search politicians by name pattern."""
        pass

    @abstractmethod
    async def upsert(self, politician: Politician) -> Politician:
        """Insert or update politician (upsert)."""
        pass
