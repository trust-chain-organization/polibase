"""ExtractedPolitician repository implementation using SQLAlchemy."""

from datetime import datetime
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.extracted_politician import ExtractedPolitician
from src.domain.repositories.extracted_politician_repository import (
    ExtractedPoliticianRepository as IExtractedPoliticianRepository,
)
from src.infrastructure.persistence.base_repository_impl import BaseRepositoryImpl


class ExtractedPoliticianModel:
    """Extracted politician database model (dynamic)."""

    id: int | None
    name: str
    party_id: int | None
    district: str | None
    position: str | None
    profile_url: str | None
    image_url: str | None
    status: str
    extracted_at: datetime
    reviewed_at: datetime | None
    reviewer_id: int | None
    created_at: datetime | None
    updated_at: datetime | None

    def __init__(self, **kwargs: Any):
        for key, value in kwargs.items():
            setattr(self, key, value)


class ExtractedPoliticianRepositoryImpl(
    BaseRepositoryImpl[ExtractedPolitician], IExtractedPoliticianRepository
):
    """Implementation of ExtractedPoliticianRepository using SQLAlchemy."""

    def __init__(self, session: AsyncSession):
        super().__init__(session, ExtractedPolitician, ExtractedPoliticianModel)

    async def create(self, entity: ExtractedPolitician) -> ExtractedPolitician:
        """Create a new extracted politician using raw SQL."""
        query = text("""
            INSERT INTO extracted_politicians (
                name, party_id, district, position, profile_url, image_url,
                status, extracted_at, reviewed_at, reviewer_id
            )
            VALUES (
                :name, :party_id, :district, :position, :profile_url, :image_url,
                :status, :extracted_at, :reviewed_at, :reviewer_id
            )
            RETURNING *
        """)

        params = {
            "name": entity.name,
            "party_id": entity.party_id,
            "district": entity.district,
            "position": entity.position,
            "profile_url": entity.profile_url,
            "image_url": entity.image_url,
            "status": entity.status,
            "extracted_at": entity.extracted_at,
            "reviewed_at": entity.reviewed_at,
            "reviewer_id": entity.reviewer_id,
        }

        result = await self.session.execute(query, params)
        row = result.fetchone()
        await self.session.commit()

        if row:
            return self._row_to_entity(row)
        raise ValueError("Failed to create extracted politician")

    async def get_by_id(self, entity_id: int) -> ExtractedPolitician | None:
        """Get extracted politician by ID using raw SQL."""
        query = text("""
            SELECT * FROM extracted_politicians
            WHERE id = :id
        """)

        result = await self.session.execute(query, {"id": entity_id})
        row = result.fetchone()

        if row:
            return self._row_to_entity(row)
        return None

    async def get_pending(
        self, party_id: int | None = None
    ) -> list[ExtractedPolitician]:
        """Get all pending politicians for review."""
        conditions = ["status = 'pending'"]
        params: dict[str, Any] = {}

        if party_id is not None:
            conditions.append("party_id = :party_id")
            params["party_id"] = party_id

        query = text(f"""
            SELECT * FROM extracted_politicians
            WHERE {" AND ".join(conditions)}
            ORDER BY extracted_at DESC
        """)

        result = await self.session.execute(query, params)
        rows = result.fetchall()

        return [self._row_to_entity(row) for row in rows]

    async def get_by_status(self, status: str) -> list[ExtractedPolitician]:
        """Get all politicians by status."""
        query = text("""
            SELECT * FROM extracted_politicians
            WHERE status = :status
            ORDER BY extracted_at DESC
        """)

        result = await self.session.execute(query, {"status": status})
        rows = result.fetchall()

        return [self._row_to_entity(row) for row in rows]

    async def get_by_party(self, party_id: int) -> list[ExtractedPolitician]:
        """Get all extracted politicians for a party."""
        query = text("""
            SELECT * FROM extracted_politicians
            WHERE party_id = :party_id
            ORDER BY name
        """)

        result = await self.session.execute(query, {"party_id": party_id})
        rows = result.fetchall()

        return [self._row_to_entity(row) for row in rows]

    async def update_status(
        self,
        politician_id: int,
        status: str,
        reviewer_id: int | None = None,
    ) -> ExtractedPolitician | None:
        """Update the status for a politician."""
        params: dict[str, Any] = {
            "politician_id": politician_id,
            "status": status,
            "updated_at": datetime.now(),
        }

        if status in ["reviewed", "approved", "rejected"]:
            params["reviewed_at"] = datetime.now()
            params["reviewer_id"] = reviewer_id
        else:
            params["reviewed_at"] = None
            params["reviewer_id"] = None

        query = text("""
            UPDATE extracted_politicians
            SET status = :status,
                reviewed_at = :reviewed_at,
                reviewer_id = :reviewer_id,
                updated_at = :updated_at
            WHERE id = :politician_id
        """)

        await self.session.execute(query, params)
        await self.session.commit()

        # Return updated entity
        return await self.get_by_id(politician_id)

    async def get_summary_by_status(self) -> dict[str, int]:
        """Get summary statistics grouped by status."""
        query = text("""
            SELECT status, COUNT(*) as count
            FROM extracted_politicians
            GROUP BY status
        """)

        result = await self.session.execute(query)
        rows = result.fetchall()

        summary = {
            "total": 0,
            "pending": 0,
            "reviewed": 0,
            "approved": 0,
            "rejected": 0,
        }

        for row in rows:
            status = row.status
            count = getattr(row, "count", 0)  # Use getattr to access the count
            if status in summary:
                summary[status] = count
            summary["total"] += count

        return summary

    async def bulk_create(
        self, politicians: list[ExtractedPolitician]
    ) -> list[ExtractedPolitician]:
        """Create multiple extracted politicians at once."""
        models = [self._to_model(politician) for politician in politicians]
        self.session.add_all(models)
        await self.session.commit()

        # Refresh all models to get IDs
        for model in models:
            await self.session.refresh(model)

        return [self._to_entity(model) for model in models]

    async def get_duplicates(
        self, name: str, party_id: int | None = None
    ) -> list[ExtractedPolitician]:
        """Find potential duplicate extracted politicians by name and party."""
        conditions = ["LOWER(name) = LOWER(:name)"]
        params: dict[str, Any] = {"name": name}

        if party_id is not None:
            conditions.append("party_id = :party_id")
            params["party_id"] = party_id

        query = text(f"""
            SELECT * FROM extracted_politicians
            WHERE {" AND ".join(conditions)}
            ORDER BY extracted_at DESC
        """)

        result = await self.session.execute(query, params)
        rows = result.fetchall()

        return [self._row_to_entity(row) for row in rows]

    def _row_to_entity(self, row: Any) -> ExtractedPolitician:
        """Convert database row to domain entity."""
        return ExtractedPolitician(
            id=row.id,
            name=row.name,
            party_id=row.party_id,
            district=row.district,
            position=row.position,
            profile_url=row.profile_url,
            image_url=row.image_url,
            status=row.status,
            extracted_at=row.extracted_at,
            reviewed_at=row.reviewed_at,
            reviewer_id=row.reviewer_id,
        )

    def _to_entity(self, model: ExtractedPoliticianModel) -> ExtractedPolitician:
        """Convert model to domain entity."""
        return ExtractedPolitician(
            id=model.id,
            name=model.name,
            party_id=model.party_id,
            district=model.district,
            position=model.position,
            profile_url=model.profile_url,
            image_url=model.image_url,
            status=model.status,
            extracted_at=model.extracted_at,
            reviewed_at=model.reviewed_at,
            reviewer_id=model.reviewer_id,
        )

    def _to_model(self, entity: ExtractedPolitician) -> ExtractedPoliticianModel:
        """Convert domain entity to model."""
        model = ExtractedPoliticianModel()
        model.id = entity.id
        model.name = entity.name
        model.party_id = entity.party_id
        model.district = entity.district
        model.position = entity.position
        model.profile_url = entity.profile_url
        model.image_url = entity.image_url
        model.status = entity.status
        model.extracted_at = entity.extracted_at
        model.reviewed_at = entity.reviewed_at
        model.reviewer_id = entity.reviewer_id
        model.created_at = entity.created_at
        model.updated_at = entity.updated_at
        return model
