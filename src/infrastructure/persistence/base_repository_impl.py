"""Base repository implementation for infrastructure layer."""

from typing import Generic, TypeVar

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from src.domain.entities.base import BaseEntity
from src.domain.repositories.base import BaseRepository

T = TypeVar("T", bound=BaseEntity)


class BaseRepositoryImpl(BaseRepository[T], Generic[T]):
    """Base implementation of repository using SQLAlchemy."""

    def __init__(self, session: AsyncSession, entity_class: type[T], model_class):
        self.session = session
        self.entity_class = entity_class
        self.model_class = model_class

    async def get_by_id(self, entity_id: int) -> T | None:
        """Get entity by ID."""
        result = await self.session.get(self.model_class, entity_id)
        if result:
            return self._to_entity(result)
        return None

    async def get_all(
        self, limit: int | None = None, offset: int | None = None
    ) -> list[T]:
        """Get all entities with optional pagination."""
        query = select(self.model_class)

        if offset:
            query = query.offset(offset)
        if limit:
            query = query.limit(limit)

        result = await self.session.execute(query)
        models = result.scalars().all()

        return [self._to_entity(model) for model in models]

    async def create(self, entity: T) -> T:
        """Create a new entity."""
        model = self._to_model(entity)
        self.session.add(model)
        await self.session.commit()
        await self.session.refresh(model)
        return self._to_entity(model)

    async def update(self, entity: T) -> T:
        """Update an existing entity."""
        if not entity.id:
            raise ValueError("Entity must have an ID to update")

        # Get existing model
        model = await self.session.get(self.model_class, entity.id)
        if not model:
            raise ValueError(f"Entity with ID {entity.id} not found")

        # Update fields
        self._update_model(model, entity)

        await self.session.commit()
        await self.session.refresh(model)
        return self._to_entity(model)

    async def delete(self, entity_id: int) -> bool:
        """Delete an entity by ID."""
        model = await self.session.get(self.model_class, entity_id)
        if not model:
            return False

        await self.session.delete(model)
        await self.session.commit()
        return True

    def _to_entity(self, model) -> T:
        """Convert database model to domain entity."""
        raise NotImplementedError("Subclass must implement _to_entity")

    def _to_model(self, entity: T):
        """Convert domain entity to database model."""
        raise NotImplementedError("Subclass must implement _to_model")

    def _update_model(self, model, entity: T):
        """Update model fields from entity."""
        raise NotImplementedError("Subclass must implement _update_model")
