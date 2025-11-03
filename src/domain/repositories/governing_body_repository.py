"""Governing body repository interface."""

from abc import abstractmethod

from src.domain.entities.governing_body import GoverningBody
from src.domain.repositories.base import BaseRepository


class GoverningBodyRepository(BaseRepository[GoverningBody]):
    """Repository interface for governing bodies."""

    @abstractmethod
    async def get_by_name_and_type(
        self, name: str, type: str | None = None
    ) -> GoverningBody | None:
        """Get governing body by name and type."""
        pass

    @abstractmethod
    async def get_by_organization_code(
        self, organization_code: str
    ) -> GoverningBody | None:
        """Get governing body by organization code."""
        pass

    @abstractmethod
    async def search_by_name(self, name_pattern: str) -> list[GoverningBody]:
        """Search governing bodies by name pattern."""
        pass

    @abstractmethod
    async def count_with_conferences(self) -> int:
        """Count governing bodies that have at least one conference."""
        pass

    @abstractmethod
    async def count_with_meetings(self) -> int:
        """Count governing bodies that have at least one meeting."""
        pass
