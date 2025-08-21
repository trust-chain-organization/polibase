"""ParliamentaryGroup repository implementation using SQLAlchemy."""

from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.parliamentary_group import ParliamentaryGroup
from src.domain.repositories.parliamentary_group_repository import (
    ParliamentaryGroupRepository as IParliamentaryGroupRepository,
)
from src.infrastructure.persistence.base_repository_impl import BaseRepositoryImpl

from .parliamentary_group_membership_repository_impl import (
    ParliamentaryGroupMembershipRepositoryImpl,
)


class ParliamentaryGroupModel:
    """Parliamentary group database model (dynamic)."""

    id: int | None
    name: str
    conference_id: int
    url: str | None
    description: str | None
    is_active: bool

    def __init__(self, **kwargs: Any):
        for key, value in kwargs.items():
            setattr(self, key, value)


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
        query = text("""
            SELECT * FROM parliamentary_groups
            WHERE name = :name AND conference_id = :conf_id
            LIMIT 1
        """)

        result = await self.session.execute(
            query, {"name": name, "conf_id": conference_id}
        )
        row = result.fetchone()

        if row:
            return self._row_to_entity(row)
        return None

    async def get_by_conference(
        self, conference_id: int, active_only: bool = True
    ) -> list[ParliamentaryGroup]:
        """Get all parliamentary groups for a conference."""
        conditions = ["conference_id = :conf_id"]
        params: dict[str, Any] = {"conf_id": conference_id}

        if active_only:
            conditions.append("is_active = TRUE")

        query = text(f"""
            SELECT * FROM parliamentary_groups
            WHERE {" AND ".join(conditions)}
            ORDER BY name
        """)

        result = await self.session.execute(query, params)
        rows = result.fetchall()

        return [self._row_to_entity(row) for row in rows]

    async def get_active(self) -> list[ParliamentaryGroup]:
        """Get all active parliamentary groups."""
        query = text("""
            SELECT * FROM parliamentary_groups
            WHERE is_active = TRUE
            ORDER BY name
        """)

        result = await self.session.execute(query)
        rows = result.fetchall()

        return [self._row_to_entity(row) for row in rows]

    def _row_to_entity(self, row: Any) -> ParliamentaryGroup:
        """Convert database row to domain entity."""
        return ParliamentaryGroup(
            id=row.id,
            name=row.name,
            conference_id=row.conference_id,
            url=getattr(row, "url", None),
            description=row.description,
            is_active=row.is_active,
        )

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

        if entity.url is not None:
            model.url = entity.url


__all__ = [
    "ParliamentaryGroupRepositoryImpl",
    "ParliamentaryGroupMembershipRepositoryImpl",
]
