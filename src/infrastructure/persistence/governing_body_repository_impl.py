"""GoverningBody repository implementation using SQLAlchemy."""

from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.governing_body import GoverningBody
from src.domain.repositories.governing_body_repository import (
    GoverningBodyRepository as IGoverningBodyRepository,
)
from src.infrastructure.persistence.base_repository_impl import BaseRepositoryImpl


class GoverningBodyModel:
    """Governing body database model (dynamic)."""

    id: int | None
    name: str
    type: str | None
    organization_code: str | None
    organization_type: str | None

    def __init__(self, **kwargs: Any):
        for key, value in kwargs.items():
            setattr(self, key, value)


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
        conditions = ["name = :name"]
        params: dict[str, Any] = {"name": name}

        if type is not None:
            conditions.append("type = :type")
            params["type"] = type

        query = text(f"""
            SELECT * FROM governing_bodies
            WHERE {" AND ".join(conditions)}
            LIMIT 1
        """)

        result = await self.session.execute(query, params)
        row = result.fetchone()

        if row:
            return self._row_to_entity(row)
        return None

    async def get_by_organization_code(
        self, organization_code: str
    ) -> GoverningBody | None:
        """Get governing body by organization code."""
        query = text("""
            SELECT * FROM governing_bodies
            WHERE organization_code = :org_code
            LIMIT 1
        """)

        result = await self.session.execute(query, {"org_code": organization_code})
        row = result.fetchone()

        if row:
            return self._row_to_entity(row)
        return None

    async def search_by_name(self, name_pattern: str) -> list[GoverningBody]:
        """Search governing bodies by name pattern."""
        query = text("""
            SELECT * FROM governing_bodies
            WHERE name ILIKE :pattern
            ORDER BY name
        """)

        result = await self.session.execute(query, {"pattern": f"%{name_pattern}%"})
        rows = result.fetchall()

        return [self._row_to_entity(row) for row in rows]

    def _row_to_entity(self, row: Any) -> GoverningBody:
        """Convert database row to domain entity."""
        return GoverningBody(
            id=row.id,
            name=row.name,
            type=row.type,
            organization_code=getattr(row, "organization_code", None),
            organization_type=getattr(row, "organization_type", None),
        )

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

        if entity.organization_code is not None:
            model.organization_code = entity.organization_code
        if entity.organization_type is not None:
            model.organization_type = entity.organization_type
