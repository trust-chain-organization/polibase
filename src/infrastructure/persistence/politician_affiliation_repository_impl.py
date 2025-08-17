"""PoliticianAffiliation repository implementation using SQLAlchemy."""

from datetime import date

from sqlalchemy import and_, update
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.politician_affiliation import PoliticianAffiliation
from src.domain.repositories.politician_affiliation_repository import (
    PoliticianAffiliationRepository as IPoliticianAffiliationRepository,
)
from src.infrastructure.persistence.base_repository_impl import BaseRepositoryImpl
from src.models.politician_affiliation import (
    PoliticianAffiliation as PoliticianAffiliationModel,
)


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
        query = select(PoliticianAffiliationModel).where(
            and_(
                PoliticianAffiliationModel.politician_id == politician_id,
                PoliticianAffiliationModel.conference_id == conference_id,
            )
        )

        if active_only:
            query = query.where(PoliticianAffiliationModel.end_date.is_(None))

        result = await self.session.execute(query)
        models = result.scalars().all()

        return [self._to_entity(model) for model in models]

    async def get_by_conference(
        self, conference_id: int, active_only: bool = True
    ) -> list[PoliticianAffiliation]:
        """Get all affiliations for a conference."""
        query = select(PoliticianAffiliationModel).where(
            PoliticianAffiliationModel.conference_id == conference_id
        )

        if active_only:
            query = query.where(PoliticianAffiliationModel.end_date.is_(None))

        result = await self.session.execute(query)
        models = result.scalars().all()

        return [self._to_entity(model) for model in models]

    async def get_by_politician(
        self, politician_id: int, active_only: bool = True
    ) -> list[PoliticianAffiliation]:
        """Get all affiliations for a politician."""
        query = select(PoliticianAffiliationModel).where(
            PoliticianAffiliationModel.politician_id == politician_id
        )

        if active_only:
            query = query.where(PoliticianAffiliationModel.end_date.is_(None))

        result = await self.session.execute(query)
        models = result.scalars().all()

        return [self._to_entity(model) for model in models]

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
        query = select(PoliticianAffiliationModel).where(
            and_(
                PoliticianAffiliationModel.politician_id == politician_id,
                PoliticianAffiliationModel.conference_id == conference_id,
                PoliticianAffiliationModel.start_date == start_date,
            )
        )

        result = await self.session.execute(query)
        existing = result.scalar_one_or_none()

        if existing:
            # Update existing
            existing.end_date = end_date
            existing.role = role
            await self.session.commit()
            await self.session.refresh(existing)
            return self._to_entity(existing)
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
        stmt = (
            update(PoliticianAffiliationModel)
            .where(PoliticianAffiliationModel.id == affiliation_id)
            .values(end_date=end_date)
        )

        await self.session.execute(stmt)
        await self.session.commit()

        # Return updated entity
        return await self.get_by_id(affiliation_id)

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
