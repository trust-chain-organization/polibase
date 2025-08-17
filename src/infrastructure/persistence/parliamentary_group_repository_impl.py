"""ParliamentaryGroup repository implementation using SQLAlchemy."""

from sqlalchemy import and_
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.parliamentary_group import ParliamentaryGroup
from src.domain.repositories.parliamentary_group_repository import (
    ParliamentaryGroupRepository as IParliamentaryGroupRepository,
)
from src.infrastructure.persistence.base_repository_impl import BaseRepositoryImpl
from src.models.parliamentary_group import ParliamentaryGroup as ParliamentaryGroupModel


class ParliamentaryGroupRepositoryImpl(
    BaseRepositoryImpl[ParliamentaryGroup], IParliamentaryGroupRepository
):
    """Implementation of ParliamentaryGroupRepository using SQLAlchemy."""

    def __init__(self, session: AsyncSession):
        super().__init__(session, ParliamentaryGroup, ParliamentaryGroupModel)

    async def get_by_name_and_conference(
        self, name: str, conference_id: int
    ) -> ParliamentaryGroup | None:
        """Get parliamentary group by name and conference."""
        query = select(ParliamentaryGroupModel).where(
            and_(
                ParliamentaryGroupModel.name == name,
                ParliamentaryGroupModel.conference_id == conference_id,
            )
        )

        result = await self.session.execute(query)
        model = result.scalar_one_or_none()

        if model:
            return self._to_entity(model)
        return None

    async def get_by_conference(
        self, conference_id: int, active_only: bool = True
    ) -> list[ParliamentaryGroup]:
        """Get all parliamentary groups for a conference."""
        query = select(ParliamentaryGroupModel).where(
            ParliamentaryGroupModel.conference_id == conference_id
        )

        if active_only:
            query = query.where(ParliamentaryGroupModel.is_active.is_(True))

        result = await self.session.execute(query)
        models = result.scalars().all()

        return [self._to_entity(model) for model in models]

    async def get_active(self) -> list[ParliamentaryGroup]:
        """Get all active parliamentary groups."""
        query = select(ParliamentaryGroupModel).where(
            ParliamentaryGroupModel.is_active.is_(True)
        )

        result = await self.session.execute(query)
        models = result.scalars().all()

        return [self._to_entity(model) for model in models]

    def _to_entity(self, model: ParliamentaryGroupModel) -> ParliamentaryGroup:
        """Convert database model to domain entity."""
        return ParliamentaryGroup(
            id=model.id,
            name=model.name,
            conference_id=model.conference_id,
            url=getattr(model, "url", None),
            description=model.description,
            is_active=model.is_active,
        )

    def _to_model(self, entity: ParliamentaryGroup) -> ParliamentaryGroupModel:
        """Convert domain entity to database model."""
        data = {
            "name": entity.name,
            "conference_id": entity.conference_id,
            "description": entity.description,
            "is_active": entity.is_active,
        }

        if entity.url is not None:
            data["url"] = entity.url
        if entity.id is not None:
            data["id"] = entity.id

        return ParliamentaryGroupModel(**data)

    def _update_model(
        self, model: ParliamentaryGroupModel, entity: ParliamentaryGroup
    ) -> None:
        """Update model fields from entity."""
        model.name = entity.name
        model.conference_id = entity.conference_id
        model.description = entity.description
        model.is_active = entity.is_active

        if hasattr(model, "url"):
            model.url = entity.url
