"""
Template for creating a repository interface in the Domain layer.

Replace:
- EntityName: Your entity name
- IEntityNameRepository: Your repository interface name
"""

from typing import Protocol
from src.domain.entities.entity_name import EntityName  # Replace with your entity
from src.domain.repositories.base_repository import BaseRepository


class IEntityNameRepository(BaseRepository[EntityName], Protocol):
    """
    Repository interface for EntityName operations.

    This interface defines the contract for data access operations.
    Implementation details are in the Infrastructure layer.
    """

    # Common CRUD operations inherited from BaseRepository:
    # - async def find_by_id(self, id: int) -> EntityName | None
    # - async def find_all(self) -> list[EntityName]
    # - async def save(self, entity: EntityName) -> EntityName
    # - async def delete(self, id: int) -> bool

    # Add custom query methods here
    async def find_by_name(self, name: str) -> list[EntityName]:
        """
        Find entities by name.

        Args:
            name: Entity name to search for

        Returns:
            List of entities matching the name
        """
        ...

    async def find_by_criteria(
        self, criteria: dict[str, any]
    ) -> list[EntityName]:
        """
        Find entities matching specific criteria.

        Args:
            criteria: Dictionary of field names and values

        Returns:
            List of matching entities
        """
        ...

    async def exists_by_name(self, name: str) -> bool:
        """
        Check if entity with given name exists.

        Args:
            name: Entity name to check

        Returns:
            True if exists, False otherwise
        """
        ...

    # Add more custom methods as needed
    # Keep them focused on data access, not business logic
