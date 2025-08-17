"""PoliticianAffiliation repository implementation using SQLAlchemy."""

from datetime import date
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.politician_affiliation import PoliticianAffiliation
from src.domain.repositories.politician_affiliation_repository import (
    PoliticianAffiliationRepository as IPoliticianAffiliationRepository,
)
from src.infrastructure.persistence.base_repository_impl import BaseRepositoryImpl


class PoliticianAffiliationModel:
    """Politician affiliation database model (dynamic)."""

    id: int | None
    politician_id: int
    conference_id: int
    start_date: date
    end_date: date | None
    role: str | None

    def __init__(self, **kwargs: Any):
        for key, value in kwargs.items():
            setattr(self, key, value)


class PoliticianAffiliationRepositoryImpl(
    BaseRepositoryImpl[PoliticianAffiliation], IPoliticianAffiliationRepository
):
    """Implementation of PoliticianAffiliationRepository using SQLAlchemy."""

    def __init__(self, session: AsyncSession):
        super().__init__(session, PoliticianAffiliation, PoliticianAffiliationModel)

    async def get_by_politician_and_conference(
        self, politician_id: int, conference_id: int, active_only: bool = True
    ) -> list[PoliticianAffiliation]:
        """Get affiliations by politician and conference."""
        conditions = ["politician_id = :pol_id", "conference_id = :conf_id"]
        params: dict[str, Any] = {"pol_id": politician_id, "conf_id": conference_id}

        if active_only:
            conditions.append("end_date IS NULL")

        query = text(f"""
            SELECT * FROM politician_affiliations
            WHERE {" AND ".join(conditions)}
            ORDER BY start_date DESC
        """)

        result = await self.session.execute(query, params)
        rows = result.fetchall()

        return [self._row_to_entity(row) for row in rows]

    async def get_by_conference(
        self, conference_id: int, active_only: bool = True
    ) -> list[PoliticianAffiliation]:
        """Get all affiliations for a conference."""
        conditions = ["conference_id = :conf_id"]
        params: dict[str, Any] = {"conf_id": conference_id}

        if active_only:
            conditions.append("end_date IS NULL")

        query = text(f"""
            SELECT * FROM politician_affiliations
            WHERE {" AND ".join(conditions)}
            ORDER BY start_date DESC
        """)

        result = await self.session.execute(query, params)
        rows = result.fetchall()

        return [self._row_to_entity(row) for row in rows]

    async def get_by_politician(
        self, politician_id: int, active_only: bool = True
    ) -> list[PoliticianAffiliation]:
        """Get all affiliations for a politician."""
        conditions = ["politician_id = :pol_id"]
        params: dict[str, Any] = {"pol_id": politician_id}

        if active_only:
            conditions.append("end_date IS NULL")

        query = text(f"""
            SELECT * FROM politician_affiliations
            WHERE {" AND ".join(conditions)}
            ORDER BY start_date DESC
        """)

        result = await self.session.execute(query, params)
        rows = result.fetchall()

        return [self._row_to_entity(row) for row in rows]

    async def upsert(
        self,
        politician_id: int,
        conference_id: int,
        start_date: date,
        end_date: date | None = None,
        role: str | None = None,
    ) -> PoliticianAffiliation:
        """Create or update an affiliation."""
        # Check if affiliation already exists
        query = text("""
            SELECT * FROM politician_affiliations
            WHERE politician_id = :pol_id
              AND conference_id = :conf_id
              AND start_date = :start_date
            LIMIT 1
        """)

        result = await self.session.execute(
            query,
            {
                "pol_id": politician_id,
                "conf_id": conference_id,
                "start_date": start_date,
            },
        )
        existing_row = result.fetchone()

        if existing_row:
            # Update existing
            update_stmt = text("""
                UPDATE politician_affiliations
                SET end_date = :end_date, role = :role
                WHERE id = :id
            """)
            await self.session.execute(
                update_stmt, {"id": existing_row.id, "end_date": end_date, "role": role}
            )
            await self.session.commit()
            return self._row_to_entity(existing_row)
        else:
            # Create new
            entity = PoliticianAffiliation(
                politician_id=politician_id,
                conference_id=conference_id,
                start_date=start_date,
                end_date=end_date,
                role=role,
            )
            return await self.create(entity)

    async def end_affiliation(
        self, affiliation_id: int, end_date: date
    ) -> PoliticianAffiliation | None:
        """End an affiliation by setting the end date."""
        query = text("""
            UPDATE politician_affiliations
            SET end_date = :end_date
            WHERE id = :id
        """)

        await self.session.execute(query, {"id": affiliation_id, "end_date": end_date})
        await self.session.commit()

        # Return updated entity
        return await self.get_by_id(affiliation_id)

    def _row_to_entity(self, row: Any) -> PoliticianAffiliation:
        """Convert database row to domain entity."""
        return PoliticianAffiliation(
            id=row.id,
            politician_id=row.politician_id,
            conference_id=row.conference_id,
            start_date=row.start_date,
            end_date=row.end_date,
            role=getattr(row, "role", None),
        )

    def _to_entity(self, model: PoliticianAffiliationModel) -> PoliticianAffiliation:
        """Convert database model to domain entity."""
        return PoliticianAffiliation(
            id=model.id,
            politician_id=model.politician_id,
            conference_id=model.conference_id,
            start_date=model.start_date,
            end_date=model.end_date,
            role=model.role,
        )

    def _to_model(self, entity: PoliticianAffiliation) -> PoliticianAffiliationModel:
        """Convert domain entity to database model."""
        data = {
            "politician_id": entity.politician_id,
            "conference_id": entity.conference_id,
            "start_date": entity.start_date,
            "end_date": entity.end_date,
            "role": entity.role,
        }

        if entity.id is not None:
            data["id"] = entity.id

        return PoliticianAffiliationModel(**data)

    def _update_model(
        self,
        model: PoliticianAffiliationModel,
        entity: PoliticianAffiliation,
    ) -> None:
        """Update model fields from entity."""
        model.politician_id = entity.politician_id
        model.conference_id = entity.conference_id
        model.start_date = entity.start_date
        model.end_date = entity.end_date
        model.role = entity.role
