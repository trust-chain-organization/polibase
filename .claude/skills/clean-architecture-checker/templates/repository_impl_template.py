"""
Template for creating a repository implementation in the Infrastructure layer.

Replace:
- EntityName: Your entity name
- EntityNameModel: Your SQLAlchemy model name
- IEntityNameRepository: Your repository interface name
- EntityNameRepositoryImpl: Your implementation class name
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.entity_name import EntityName
from src.domain.repositories.entity_name_repository import IEntityNameRepository
from src.infrastructure.persistence.base_repository import BaseRepositoryImpl
from src.infrastructure.persistence.models.entity_name import (
    EntityName as EntityNameModel,
)


class EntityNameRepositoryImpl(
    BaseRepositoryImpl[EntityName], IEntityNameRepository
):
    """
    SQLAlchemy implementation of IEntityNameRepository.

    Handles conversion between domain entities and database models.
    """

    def __init__(self, session: AsyncSession):
        """
        Initialize repository with database session.

        Args:
            session: SQLAlchemy async session
        """
        super().__init__(session, EntityNameModel, EntityName)

    # Implement custom query methods from interface

    async def find_by_name(self, name: str) -> list[EntityName]:
        """Find entities by name."""
        query = select(EntityNameModel).where(EntityNameModel.name == name)
        result = await self.session.execute(query)
        models = result.scalars().all()
        return [self._to_entity(model) for model in models]

    async def find_by_criteria(
        self, criteria: dict[str, any]
    ) -> list[EntityName]:
        """Find entities matching criteria."""
        query = select(EntityNameModel)

        # Build query dynamically based on criteria
        for key, value in criteria.items():
            if hasattr(EntityNameModel, key):
                query = query.where(getattr(EntityNameModel, key) == value)

        result = await self.session.execute(query)
        models = result.scalars().all()
        return [self._to_entity(model) for model in models]

    async def exists_by_name(self, name: str) -> bool:
        """Check if entity with given name exists."""
        query = select(EntityNameModel).where(EntityNameModel.name == name)
        result = await self.session.execute(query)
        return result.scalar_one_or_none() is not None

    # Conversion methods

    def _to_entity(self, model: EntityNameModel) -> EntityName:
        """
        Convert SQLAlchemy model to domain entity.

        Args:
            model: SQLAlchemy model instance

        Returns:
            Domain entity instance
        """
        return EntityName(
            id=model.id,
            name=model.name,
            # Map other fields here
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    def _to_model(self, entity: EntityName) -> EntityNameModel:
        """
        Convert domain entity to SQLAlchemy model.

        Args:
            entity: Domain entity instance

        Returns:
            SQLAlchemy model instance
        """
        return EntityNameModel(
            id=entity.id,
            name=entity.name,
            # Map other fields here
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )
