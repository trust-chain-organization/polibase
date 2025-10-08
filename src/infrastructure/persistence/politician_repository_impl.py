"""Politician repository implementation (async-only)."""

import logging
from typing import Any

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError as SQLIntegrityError
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.politician import Politician
from src.domain.repositories.politician_repository import PoliticianRepository
from src.infrastructure.persistence.base_repository_impl import BaseRepositoryImpl

logger = logging.getLogger(__name__)


class PoliticianModel:
    """Politician database model (dynamic)."""

    def __init__(self, **kwargs: Any):
        for key, value in kwargs.items():
            setattr(self, key, value)


class PoliticianRepositoryImpl(BaseRepositoryImpl[Politician], PoliticianRepository):
    """Async-only implementation of politician repository using SQLAlchemy."""

    def __init__(
        self,
        session: AsyncSession,
        model_class: type[Any] | None = None,
    ):
        """Initialize repository.

        Args:
            session: Async database session
            model_class: Optional model class for compatibility
        """
        # Use dynamic model if no model class provided
        if model_class is None:
            model_class = PoliticianModel

        super().__init__(session, Politician, model_class)

    async def get_by_name_and_party(
        self, name: str, political_party_id: int | None = None
    ) -> Politician | None:
        """Get politician by name and political party."""
        conditions = ["name = :name"]
        params: dict[str, Any] = {"name": name}

        if political_party_id is not None:
            conditions.append("political_party_id = :party_id")
            params["party_id"] = political_party_id

        query = text(f"""
            SELECT * FROM politicians
            WHERE {" AND ".join(conditions)}
            LIMIT 1
        """)
        result = await self.session.execute(query, params)
        row = result.fetchone()
        return self._row_to_entity(row) if row else None

    async def get_by_party(self, political_party_id: int) -> list[Politician]:
        """Get all politicians for a political party."""
        query = text("""
            SELECT * FROM politicians
            WHERE political_party_id = :party_id
            ORDER BY name
        """)
        result = await self.session.execute(query, {"party_id": political_party_id})
        rows = result.fetchall()
        return [self._row_to_entity(row) for row in rows]

    async def search_by_name(self, name_pattern: str) -> list[Politician]:
        """Search politicians by name pattern."""
        query = text("""
            SELECT * FROM politicians
            WHERE name ILIKE :pattern
            ORDER BY name
        """)
        result = await self.session.execute(query, {"pattern": f"%{name_pattern}%"})
        rows = result.fetchall()
        return [self._row_to_entity(row) for row in rows]

    async def upsert(self, politician: Politician) -> Politician:
        """Insert or update politician (upsert)."""
        # Check if exists
        existing = await self.get_by_name_and_party(
            politician.name,
            politician.political_party_id,
        )

        if existing:
            # Update existing
            politician.id = existing.id
            return await self.update(politician)
        else:
            # Create new using base class create (which commits)
            return await self.create(politician)

    async def bulk_create_politicians(
        self, politicians_data: list[dict[str, Any]]
    ) -> dict[str, list[Politician] | list[dict[str, Any]]]:
        """Bulk create or update politicians.

        Returns dict for backward compatibility with legacy code.
        """
        created: list[Politician] = []
        updated: list[Politician] = []
        errors: list[dict[str, Any]] = []

        for data in politicians_data:
            try:
                # Check existing politician
                existing = await self.get_by_name_and_party(
                    data.get("name", ""),
                    data.get("political_party_id"),
                )

                if existing:
                    # Update if needed
                    needs_update = False
                    for field in [
                        "prefecture",
                        "electoral_district",
                        "profile_url",
                        "party_position",
                    ]:
                        if field in data and data[field] != getattr(
                            existing, field, None
                        ):
                            setattr(existing, field, data[field])
                            needs_update = True

                    if needs_update:
                        updated_politician = await self.update(existing)
                        updated.append(updated_politician)
                else:
                    # Create new politician
                    new_politician = Politician(
                        name=data.get("name", ""),
                        political_party_id=data.get("political_party_id"),
                        district=data.get("electoral_district"),
                        profile_page_url=data.get("profile_url"),
                    )
                    created_politician = await self.create_entity(new_politician)
                    created.append(created_politician)

            except SQLIntegrityError as e:
                logger.error(
                    f"Integrity error processing politician {data.get('name')}: {e}"
                )
                errors.append(
                    {
                        "data": data,
                        "error": f"Duplicate or constraint violation: {str(e)}",
                    }
                )
            except SQLAlchemyError as e:
                logger.error(
                    f"Database error processing politician {data.get('name')}: {e}"
                )
                errors.append({"data": data, "error": f"Database error: {str(e)}"})
            except Exception as e:
                logger.error(
                    f"Unexpected error processing politician {data.get('name')}: {e}"
                )
                errors.append({"data": data, "error": f"Unexpected error: {str(e)}"})

        # Commit changes
        await self.session.commit()

        return {"created": created, "updated": updated, "errors": errors}

    async def fetch_as_dict_async(
        self, query: str, params: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        """Execute raw SQL query and return results as dictionaries (async)."""
        result = await self.session.execute(text(query), params or {})
        rows = result.fetchall()
        return [dict(row._mapping) for row in rows]  # type: ignore[attr-defined]

    async def create_entity(self, entity: Politician) -> Politician:
        """Create a new politician entity (async) without committing."""
        # Create without committing (for bulk operations)
        model = self._to_model(entity)

        self.session.add(model)
        # Don't commit here - let the caller decide when to commit
        await self.session.flush()  # Flush to get the ID without committing
        await self.session.refresh(model)

        return self._to_entity(model)

    async def get_all(
        self, limit: int | None = None, offset: int | None = 0
    ) -> list[Politician]:
        """Get all politicians."""
        query_text = """
            SELECT p.*, pp.name as party_name
            FROM politicians p
            LEFT JOIN political_parties pp ON p.political_party_id = pp.id
            ORDER BY p.name
        """
        params = {}

        if limit is not None:
            query_text += " LIMIT :limit OFFSET :offset"
            params = {"limit": limit, "offset": offset or 0}

        result = await self.session.execute(
            text(query_text), params if params else None
        )
        rows = result.fetchall()

        return [self._row_to_entity(row) for row in rows]

    async def get_by_id(self, entity_id: int) -> Politician | None:
        """Get politician by ID."""
        query = text("""
            SELECT p.*, pp.name as party_name
            FROM politicians p
            LEFT JOIN political_parties pp ON p.political_party_id = pp.id
            WHERE p.id = :id
        """)

        result = await self.session.execute(query, {"id": entity_id})
        row = result.fetchone()

        if row:
            return self._row_to_entity(row)
        return None

    async def create(self, entity: Politician) -> Politician:
        """Create a new politician."""
        query = text("""
            INSERT INTO politicians (
                name, political_party_id,
                electoral_district, profile_url, furigana
            )
            VALUES (
                :name, :political_party_id,
                :electoral_district, :profile_url, :furigana
            )
            RETURNING *
        """)

        params = {
            "name": entity.name,
            "political_party_id": entity.political_party_id,
            # Map district to electoral_district
            "electoral_district": entity.district,
            # Map profile_page_url to profile_url
            "profile_url": entity.profile_page_url,
            "furigana": entity.furigana,
        }

        result = await self.session.execute(query, params)
        await self.session.commit()

        row = result.first()
        if row:
            return self._row_to_entity(row)
        raise RuntimeError("Failed to create politician")

    async def update(self, entity: Politician) -> Politician:
        """Update an existing politician."""
        from src.infrastructure.exceptions import UpdateError

        query = text("""
            UPDATE politicians
            SET name = :name,
                political_party_id = :political_party_id,
                electoral_district = :electoral_district,
                profile_url = :profile_url,
                furigana = :furigana
            WHERE id = :id
            RETURNING *
        """)

        params = {
            "id": entity.id,
            "name": entity.name,
            "political_party_id": entity.political_party_id,
            # Map district to electoral_district
            "electoral_district": entity.district,
            # Map profile_page_url to profile_url
            "profile_url": entity.profile_page_url,
            "furigana": entity.furigana,
        }

        result = await self.session.execute(query, params)
        await self.session.commit()

        row = result.first()
        if row:
            return self._row_to_entity(row)
        raise UpdateError(f"Politician with ID {entity.id} not found")

    async def delete(self, entity_id: int) -> bool:
        """Delete a politician by ID."""
        query = text("DELETE FROM politicians WHERE id = :id")

        result = await self.session.execute(query, {"id": entity_id})
        await self.session.commit()

        return result.rowcount > 0  # type: ignore[attr-defined]

    async def count_by_party(self, political_party_id: int) -> int:
        """Count politicians by political party."""
        query = text("""
            SELECT COUNT(*) as count
            FROM politicians
            WHERE political_party_id = :party_id
        """)

        result = await self.session.execute(query, {"party_id": political_party_id})
        row = result.first()
        return row.count if row else 0  # type: ignore[attr-defined]

    def _row_to_entity(self, row: Any) -> Politician:
        """Convert database row to domain entity."""
        if row is None:
            raise ValueError("Cannot convert None to Politician entity")

        # Handle both Row and dict objects
        if hasattr(row, "_mapping"):
            data = dict(row._mapping)  # type: ignore[attr-defined]
        elif isinstance(row, dict):
            data = row
        else:
            # Try to access as attributes
            data = {
                "id": getattr(row, "id", None),
                "name": getattr(row, "name", None),
                "political_party_id": getattr(row, "political_party_id", None),
                "prefecture": getattr(row, "prefecture", None),
                "electoral_district": getattr(row, "electoral_district", None),
                "profile_url": getattr(row, "profile_url", None),
                "party_position": getattr(row, "party_position", None),
                "furigana": getattr(row, "furigana", None),
            }

        return Politician(
            name=str(data.get("name") or ""),
            political_party_id=data.get("political_party_id"),
            furigana=data.get("furigana"),
            district=data.get(
                "electoral_district"
            ),  # Map electoral_district to district
            profile_page_url=data.get(
                "profile_url"
            ),  # Map profile_url to profile_page_url
            id=data.get("id"),
        )

    def _to_entity(self, model: Any) -> Politician:
        """Convert database model to domain entity."""
        return self._row_to_entity(model)

    def _to_model(self, entity: Politician) -> Any:
        """Convert domain entity to database model."""
        return self.model_class(
            name=entity.name,
            political_party_id=entity.political_party_id,
            prefecture=None,  # No direct mapping from entity.district
            electoral_district=entity.district,  # Map district to electoral_district
            profile_url=entity.profile_page_url,  # Map profile_page_url to profile_url
            party_position=None,  # Not in entity
            furigana=entity.furigana,
            id=entity.id,
        )

    def _update_model(self, model: Any, entity: Politician) -> None:
        """Update model fields from entity."""
        model.name = entity.name
        model.political_party_id = entity.political_party_id
        model.electoral_district = entity.district
        model.profile_url = entity.profile_page_url
        model.furigana = entity.furigana

    async def get_all_for_matching(self) -> list[dict[str, Any]]:
        """Get all politicians for matching purposes."""
        query = text("""
            SELECT p.id, p.name, p.position, p.prefecture,
                   p.electoral_district, pp.name as party_name
            FROM politicians p
            LEFT JOIN political_parties pp ON p.political_party_id = pp.id
            ORDER BY p.name
        """)
        result = await self.session.execute(query)
        rows = result.fetchall()

        return [
            {
                "id": row.id,
                "name": row.name,
                "position": row.position,
                "prefecture": row.prefecture,
                "electoral_district": row.electoral_district,
                "party_name": row.party_name,
            }
            for row in rows
        ]

    async def get_party_statistics(self) -> list[dict[str, Any]]:
        """Get politician statistics for all parties."""
        query = text("""
            WITH extracted_stats AS (
                SELECT
                    pp.id as party_id,
                    pp.name as party_name,
                    COUNT(ep.id) as extracted_total,
                    COUNT(CASE WHEN ep.status = 'pending' THEN 1 END)
                        as extracted_pending,
                    COUNT(CASE WHEN ep.status = 'reviewed' THEN 1 END)
                        as extracted_reviewed,
                    COUNT(CASE WHEN ep.status = 'approved' THEN 1 END)
                        as extracted_approved,
                    COUNT(CASE WHEN ep.status = 'rejected' THEN 1 END)
                        as extracted_rejected,
                    COUNT(CASE WHEN ep.status = 'converted' THEN 1 END)
                        as extracted_converted
                FROM political_parties pp
                LEFT JOIN extracted_politicians ep ON pp.id = ep.party_id
                GROUP BY pp.id, pp.name
            ),
            politician_stats AS (
                SELECT
                    pp.id as party_id,
                    COUNT(p.id) as politicians_total
                FROM political_parties pp
                LEFT JOIN politicians p ON pp.id = p.political_party_id
                GROUP BY pp.id
            )
            SELECT
                es.party_id,
                es.party_name,
                COALESCE(es.extracted_total, 0) as extracted_total,
                COALESCE(es.extracted_pending, 0) as extracted_pending,
                COALESCE(es.extracted_reviewed, 0) as extracted_reviewed,
                COALESCE(es.extracted_approved, 0) as extracted_approved,
                COALESCE(es.extracted_rejected, 0) as extracted_rejected,
                COALESCE(es.extracted_converted, 0) as extracted_converted,
                COALESCE(ps.politicians_total, 0) as politicians_total
            FROM extracted_stats es
            LEFT JOIN politician_stats ps ON es.party_id = ps.party_id
            ORDER BY es.party_name
        """)

        result = await self.session.execute(query)
        rows = result.fetchall()

        return [
            {
                "party_id": row.party_id,
                "party_name": row.party_name,
                "extracted_total": row.extracted_total,
                "extracted_pending": row.extracted_pending,
                "extracted_reviewed": row.extracted_reviewed,
                "extracted_approved": row.extracted_approved,
                "extracted_rejected": row.extracted_rejected,
                "extracted_converted": row.extracted_converted,
                "politicians_total": row.politicians_total,
            }
            for row in rows
        ]

    async def get_party_statistics_by_id(self, party_id: int) -> dict[str, Any] | None:
        """Get politician statistics for a specific party."""
        query = text("""
            WITH extracted_stats AS (
                SELECT
                    pp.id as party_id,
                    pp.name as party_name,
                    COUNT(ep.id) as extracted_total,
                    COUNT(CASE WHEN ep.status = 'pending' THEN 1 END)
                        as extracted_pending,
                    COUNT(CASE WHEN ep.status = 'reviewed' THEN 1 END)
                        as extracted_reviewed,
                    COUNT(CASE WHEN ep.status = 'approved' THEN 1 END)
                        as extracted_approved,
                    COUNT(CASE WHEN ep.status = 'rejected' THEN 1 END)
                        as extracted_rejected,
                    COUNT(CASE WHEN ep.status = 'converted' THEN 1 END)
                        as extracted_converted
                FROM political_parties pp
                LEFT JOIN extracted_politicians ep ON pp.id = ep.party_id
                WHERE pp.id = :party_id
                GROUP BY pp.id, pp.name
            ),
            politician_stats AS (
                SELECT
                    pp.id as party_id,
                    COUNT(p.id) as politicians_total
                FROM political_parties pp
                LEFT JOIN politicians p ON pp.id = p.political_party_id
                WHERE pp.id = :party_id
                GROUP BY pp.id
            )
            SELECT
                es.party_id,
                es.party_name,
                COALESCE(es.extracted_total, 0) as extracted_total,
                COALESCE(es.extracted_pending, 0) as extracted_pending,
                COALESCE(es.extracted_reviewed, 0) as extracted_reviewed,
                COALESCE(es.extracted_approved, 0) as extracted_approved,
                COALESCE(es.extracted_rejected, 0) as extracted_rejected,
                COALESCE(es.extracted_converted, 0) as extracted_converted,
                COALESCE(ps.politicians_total, 0) as politicians_total
            FROM extracted_stats es
            LEFT JOIN politician_stats ps ON es.party_id = ps.party_id
        """)

        result = await self.session.execute(query, {"party_id": party_id})
        row = result.fetchone()

        if row:
            return {
                "party_id": row.party_id,
                "party_name": row.party_name,
                "extracted_total": row.extracted_total,
                "extracted_pending": row.extracted_pending,
                "extracted_reviewed": row.extracted_reviewed,
                "extracted_approved": row.extracted_approved,
                "extracted_rejected": row.extracted_rejected,
                "extracted_converted": row.extracted_converted,
                "politicians_total": row.politicians_total,
            }

        return None
