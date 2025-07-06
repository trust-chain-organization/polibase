"""Base repository interface."""

from abc import ABC, abstractmethod
from typing import Generic, TypeVar

from src.domain.entities.base import BaseEntity

T = TypeVar("T", bound=BaseEntity)


class BaseRepository(ABC, Generic[T]):
    """Base repository interface for all repositories."""

    @abstractmethod
    async def get_by_id(self, entity_id: int) -> T | None:
        """Get entity by ID."""
        pass

    @abstractmethod
    async def get_all(
        self, limit: int | None = None, offset: int | None = None
    ) -> list[T]:
        """Get all entities with optional pagination."""
        pass

    @abstractmethod
    async def create(self, entity: T) -> T:
        """Create a new entity."""
        pass

    @abstractmethod
    async def update(self, entity: T) -> T:
        """Update an existing entity."""
        pass

    @abstractmethod
    async def delete(self, entity_id: int) -> bool:
        """Delete an entity by ID."""
        pass
