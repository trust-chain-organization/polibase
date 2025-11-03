"""Minutes repository interface."""

from abc import abstractmethod

from src.domain.entities.minutes import Minutes
from src.domain.repositories.base import BaseRepository


class MinutesRepository(BaseRepository[Minutes]):
    """Repository interface for minutes."""

    @abstractmethod
    async def get_by_meeting(self, meeting_id: int) -> Minutes | None:
        """Get minutes by meeting ID."""
        pass

    @abstractmethod
    async def get_unprocessed(self, limit: int | None = None) -> list[Minutes]:
        """Get minutes that haven't been processed yet."""
        pass

    @abstractmethod
    async def mark_processed(self, minutes_id: int) -> bool:
        """Mark minutes as processed."""
        pass

    @abstractmethod
    async def count_processed(self) -> int:
        """Count minutes that have been processed (processed_at IS NOT NULL)."""
        pass
