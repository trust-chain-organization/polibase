"""Speaker repository interface."""

from abc import abstractmethod

from src.domain.entities.speaker import Speaker
from src.domain.repositories.base import BaseRepository


class SpeakerRepository(BaseRepository[Speaker]):
    """Repository interface for speakers."""

    @abstractmethod
    async def get_by_name_party_position(
        self,
        name: str,
        political_party_name: str | None = None,
        position: str | None = None,
    ) -> Speaker | None:
        """Get speaker by name, party, and position."""
        pass

    @abstractmethod
    async def get_politicians(self) -> list[Speaker]:
        """Get all speakers who are politicians."""
        pass

    @abstractmethod
    async def search_by_name(self, name_pattern: str) -> list[Speaker]:
        """Search speakers by name pattern."""
        pass

    @abstractmethod
    async def upsert(self, speaker: Speaker) -> Speaker:
        """Insert or update speaker (upsert)."""
        pass

    @abstractmethod
    async def get_all_with_conversation_count(
        self, offset: int = 0, limit: int | None = None
    ) -> tuple[list[tuple[Speaker, int]], int]:
        """Get all speakers with their conversation count.

        Returns:
            Tuple of (list of (speaker, conversation_count), total_count)
        """
        pass
