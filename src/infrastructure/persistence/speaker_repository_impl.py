"""Speaker repository implementation."""

from typing import Any

from sqlalchemy import and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from src.domain.entities.speaker import Speaker
from src.domain.repositories.speaker_repository import SpeakerRepository
from src.infrastructure.persistence.base_repository_impl import BaseRepositoryImpl


class SpeakerRepositoryImpl(BaseRepositoryImpl[Speaker], SpeakerRepository):
    """Implementation of speaker repository using SQLAlchemy."""

    def __init__(self, session: AsyncSession, model_class: type[Any]):
        super().__init__(session, Speaker, model_class)

    async def get_by_name_party_position(
        self,
        name: str,
        political_party_name: str | None = None,
        position: str | None = None,
    ) -> Speaker | None:
        """Get speaker by name, party, and position."""
        conditions = [self.model_class.name == name]

        if political_party_name is not None:
            conditions.append(
                self.model_class.political_party_name == political_party_name
            )
        if position is not None:
            conditions.append(self.model_class.position == position)

        query = select(self.model_class).where(and_(*conditions))
        result = await self.session.execute(query)
        model = result.scalar_one_or_none()

        if model:
            return self._to_entity(model)
        return None

    async def get_politicians(self) -> list[Speaker]:
        """Get all speakers who are politicians."""
        query = select(self.model_class).where(self.model_class.is_politician)
        result = await self.session.execute(query)
        models = result.scalars().all()

        return [self._to_entity(model) for model in models]

    async def search_by_name(self, name_pattern: str) -> list[Speaker]:
        """Search speakers by name pattern."""
        query = select(self.model_class).where(
            self.model_class.name.ilike(f"%{name_pattern}%")
        )
        result = await self.session.execute(query)
        models = result.scalars().all()

        return [self._to_entity(model) for model in models]

    async def upsert(self, speaker: Speaker) -> Speaker:
        """Insert or update speaker (upsert)."""
        # Check if exists
        existing = await self.get_by_name_party_position(
            speaker.name,
            speaker.political_party_name,
            speaker.position,
        )

        if existing:
            # Update existing
            speaker.id = existing.id
            return await self.update(speaker)
        else:
            # Create new
            return await self.create(speaker)

    def _to_entity(self, model: Any) -> Speaker:
        """Convert database model to domain entity."""
        return Speaker(
            name=model.name,
            type=model.type,
            political_party_name=model.political_party_name,
            position=model.position,
            is_politician=model.is_politician,
            id=model.id,
        )

    def _to_model(self, entity: Speaker) -> Any:
        """Convert domain entity to database model."""
        return self.model_class(
            name=entity.name,
            type=entity.type,
            political_party_name=entity.political_party_name,
            position=entity.position,
            is_politician=entity.is_politician,
        )

    def _update_model(self, model: Any, entity: Speaker) -> None:
        """Update model fields from entity."""
        model.name = entity.name
        model.type = entity.type
        model.political_party_name = entity.political_party_name
        model.position = entity.position
        model.is_politician = entity.is_politician
