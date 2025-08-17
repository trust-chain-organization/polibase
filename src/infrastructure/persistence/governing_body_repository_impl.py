"""GoverningBody repository implementation using SQLAlchemy."""

from sqlalchemy import and_
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.governing_body import GoverningBody
from src.domain.repositories.governing_body_repository import (
    GoverningBodyRepository as IGoverningBodyRepository,
)
from src.infrastructure.persistence.base_repository_impl import BaseRepositoryImpl
from src.models.governing_body import GoverningBody as GoverningBodyModel


class GoverningBodyRepositoryImpl(
    BaseRepositoryImpl[GoverningBody], IGoverningBodyRepository
):
    """Implementation of GoverningBodyRepository using SQLAlchemy."""

    def __init__(self, session: AsyncSession):
        super().__init__(session, GoverningBody, GoverningBodyModel)

    async def get_by_name_and_type(
        self, name: str, type: str | None = None
    ) -> GoverningBody | None:
        """Get governing body by name and type."""
        query = select(GoverningBodyModel).where(GoverningBodyModel.name == name)

        if type is not None:
            query = query.where(GoverningBodyModel.type == type)

        result = await self.session.execute(query)
        model = result.scalar_one_or_none()

        if model:
            return self._to_entity(model)
        return None

    async def get_by_organization_code(
        self, organization_code: str
    ) -> GoverningBody | None:
        """Get governing body by organization code."""
        query = select(GoverningBodyModel).where(
            GoverningBodyModel.organization_code == organization_code
        )

        result = await self.session.execute(query)
        model = result.scalar_one_or_none()

        if model:
            return self._to_entity(model)
        return None

    async def search_by_name(self, name_pattern: str) -> list[GoverningBody]:
        """Search governing bodies by name pattern."""
        query = select(GoverningBodyModel).where(
            GoverningBodyModel.name.ilike(f"%{name_pattern}%")
        )

        result = await self.session.execute(query)
        models = result.scalars().all()

        return [self._to_entity(model) for model in models]

    def _to_entity(self, model: GoverningBodyModel) -> GoverningBody:
        """Convert database model to domain entity."""
        return GoverningBody(
            id=model.id,
            name=model.name,
            type=model.type,
            organization_code=getattr(model, "organization_code", None),
            organization_type=getattr(model, "organization_type", None),
        )

    def _to_model(self, entity: GoverningBody) -> GoverningBodyModel:
        """Convert domain entity to database model."""
        data = {
            "name": entity.name,
            "type": entity.type,
        }

        if entity.organization_code is not None:
            data["organization_code"] = entity.organization_code
        if entity.organization_type is not None:
            data["organization_type"] = entity.organization_type
        if entity.id is not None:
            data["id"] = entity.id

        return GoverningBodyModel(**data)

    def _update_model(self, model: GoverningBodyModel, entity: GoverningBody) -> None:
        """Update model fields from entity."""
        model.name = entity.name
        model.type = entity.type

        if hasattr(model, "organization_code"):
            model.organization_code = entity.organization_code
        if hasattr(model, "organization_type"):
            model.organization_type = entity.organization_type
