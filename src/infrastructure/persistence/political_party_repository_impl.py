"""PoliticalParty repository implementation using SQLAlchemy."""

from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.political_party import PoliticalParty
from src.domain.repositories.political_party_repository import (
    PoliticalPartyRepository as IPoliticalPartyRepository,
)
from src.infrastructure.persistence.base_repository_impl import BaseRepositoryImpl


class PoliticalPartyModel:
    """Political party database model (dynamic)."""

    id: int | None
    name: str
    members_list_url: str | None

    def __init__(self, **kwargs: Any):
        for key, value in kwargs.items():
            setattr(self, key, value)


class PoliticalPartyRepositoryImpl(
    BaseRepositoryImpl[PoliticalParty], IPoliticalPartyRepository
):
    """Implementation of PoliticalPartyRepository using SQLAlchemy."""

    def __init__(self, session: AsyncSession):
        super().__init__(session, PoliticalParty, PoliticalPartyModel)

    async def get_by_name(self, name: str) -> PoliticalParty | None:
        """Get political party by name."""
        query = text("""
            SELECT * FROM political_parties
            WHERE name = :name
            LIMIT 1
        """)

        result = await self.session.execute(query, {"name": name})
        row = result.fetchone()

        if row:
            return self._row_to_entity(row)
        return None

    async def get_with_members_url(self) -> list[PoliticalParty]:
        """Get political parties that have members list URL."""
        query = text("""
            SELECT * FROM political_parties
            WHERE members_list_url IS NOT NULL
            ORDER BY name
        """)

        result = await self.session.execute(query)
        rows = result.fetchall()

        return [self._row_to_entity(row) for row in rows]

    async def search_by_name(self, name_pattern: str) -> list[PoliticalParty]:
        """Search political parties by name pattern."""
        query = text("""
            SELECT * FROM political_parties
            WHERE name ILIKE :pattern
            ORDER BY name
        """)

        result = await self.session.execute(query, {"pattern": f"%{name_pattern}%"})
        rows = result.fetchall()

        return [self._row_to_entity(row) for row in rows]

    def _row_to_entity(self, row: Any) -> PoliticalParty:
        """Convert database row to domain entity."""
        return PoliticalParty(
            id=row.id,
            name=row.name,
            members_list_url=row.members_list_url,
        )

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
