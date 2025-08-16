"""Speaker repository interface."""

from abc import abstractmethod
from typing import Any

from src.application.dtos.speaker_dto import SpeakerWithConversationCountDTO
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
    async def get_speakers_with_conversation_count(
        self,
        limit: int | None = None,
        offset: int | None = None,
        speaker_type: str | None = None,
        is_politician: bool | None = None,
    ) -> list[SpeakerWithConversationCountDTO]:
        """Get speakers with their conversation count."""
        pass

    @abstractmethod
    async def find_by_name(self, name: str) -> Speaker | None:
        """Find speaker by name."""
        pass

    @abstractmethod
    async def get_speakers_not_linked_to_politicians(self) -> list[Speaker]:
        """Get speakers who are not linked to politicians (is_politician=False)."""
        pass

    @abstractmethod
    async def get_speakers_with_politician_info(self) -> list[dict[str, Any]]:
        """Get speakers with linked politician information."""
        pass

    @abstractmethod
    async def get_speaker_politician_stats(self) -> dict[str, int | float]:
        """Get statistics of speaker-politician linkage."""
        pass
