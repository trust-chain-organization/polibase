"""Conversation repository interface."""

from abc import abstractmethod

from src.domain.entities.conversation import Conversation
from src.domain.repositories.base import BaseRepository


class ConversationRepository(BaseRepository[Conversation]):
    """Repository interface for conversations."""

    @abstractmethod
    async def get_by_minutes(self, minutes_id: int) -> list[Conversation]:
        """Get all conversations for a minutes record."""
        pass

    @abstractmethod
    async def get_by_speaker(
        self, speaker_id: int, limit: int | None = None
    ) -> list[Conversation]:
        """Get all conversations by a speaker."""
        pass

    @abstractmethod
    async def get_unlinked(self, limit: int | None = None) -> list[Conversation]:
        """Get conversations without speaker links."""
        pass

    @abstractmethod
    async def bulk_create(
        self, conversations: list[Conversation]
    ) -> list[Conversation]:
        """Create multiple conversations at once."""
        pass
