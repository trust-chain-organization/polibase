"""Parliamentary group repository interface."""

from abc import abstractmethod

from src.domain.entities.parliamentary_group import ParliamentaryGroup
from src.domain.repositories.base import BaseRepository


class ParliamentaryGroupRepository(BaseRepository[ParliamentaryGroup]):
    """Repository interface for parliamentary groups."""

    @abstractmethod
    async def get_by_name_and_conference(
        self, name: str, conference_id: int
    ) -> ParliamentaryGroup | None:
        """Get parliamentary group by name and conference."""
        pass

    @abstractmethod
    async def get_by_conference_id(
        self, conference_id: int, active_only: bool = True
    ) -> list[ParliamentaryGroup]:
        """Get all parliamentary groups for a conference."""
        pass

    @abstractmethod
    async def get_active(self) -> list[ParliamentaryGroup]:
        """Get all active parliamentary groups."""
        pass
