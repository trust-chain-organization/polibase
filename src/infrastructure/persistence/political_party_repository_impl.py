"""PoliticalParty repository implementation using SQLAlchemy."""

from sqlalchemy import and_
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.political_party import PoliticalParty
from src.domain.repositories.political_party_repository import (
    PoliticalPartyRepository as IPoliticalPartyRepository,
)
from src.infrastructure.persistence.base_repository_impl import BaseRepositoryImpl
from src.models.political_party import PoliticalParty as PoliticalPartyModel


class PoliticalPartyRepositoryImpl(
    BaseRepositoryImpl[PoliticalParty], IPoliticalPartyRepository
):
    """Implementation of PoliticalPartyRepository using SQLAlchemy."""

    def __init__(self, session: AsyncSession):
        super().__init__(session, PoliticalParty, PoliticalPartyModel)

    async def get_by_name(self, name: str) -> PoliticalParty | None:
        """Get political party by name."""
        query = select(PoliticalPartyModel).where(PoliticalPartyModel.name == name)

        result = await self.session.execute(query)
        model = result.scalar_one_or_none()

        if model:
            return self._to_entity(model)
        return None

    async def get_with_members_url(self) -> list[PoliticalParty]:
        """Get political parties that have members list URL."""
        query = select(PoliticalPartyModel).where(
            PoliticalPartyModel.members_list_url.isnot(None)
        )

        result = await self.session.execute(query)
        models = result.scalars().all()

        return [self._to_entity(model) for model in models]

    async def search_by_name(self, name_pattern: str) -> list[PoliticalParty]:
        """Search political parties by name pattern."""
        query = select(PoliticalPartyModel).where(
            PoliticalPartyModel.name.ilike(f"%{name_pattern}%")
        )

        result = await self.session.execute(query)
        models = result.scalars().all()

        return [self._to_entity(model) for model in models]

    def _to_entity(self, model: PoliticalPartyModel) -> PoliticalParty:
        """Convert database model to domain entity."""
        return PoliticalParty(
            id=model.id,
            name=model.name,
            members_list_url=model.members_list_url,
        )

    def _to_model(self, entity: PoliticalParty) -> PoliticalPartyModel:
        """Convert domain entity to database model."""
        data = {
            "name": entity.name,
            "members_list_url": entity.members_list_url,
        }

        if entity.id is not None:
            data["id"] = entity.id

        return PoliticalPartyModel(**data)

    def _update_model(self, model: PoliticalPartyModel, entity: PoliticalParty) -> None:
        """Update model fields from entity."""
        model.name = entity.name
        model.members_list_url = entity.members_list_url
