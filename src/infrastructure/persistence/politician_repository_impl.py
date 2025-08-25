"""Politician repository implementation."""

import logging
from datetime import datetime
from typing import Any

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError as SQLIntegrityError
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from src.database.typed_repository import TypedRepository
from src.domain.entities.politician import Politician
from src.domain.repositories.politician_repository import PoliticianRepository
from src.infrastructure.persistence.base_repository_impl import BaseRepositoryImpl
from src.models.politician import PoliticianCreate, PoliticianUpdate

# Type alias for SQL parameters
SQLParam = str | int | float | bool | datetime | None

logger = logging.getLogger(__name__)


class PoliticianModel:
    """Politician database model (dynamic)."""

    def __init__(self, **kwargs: Any):
        for key, value in kwargs.items():
            setattr(self, key, value)


class PoliticianRepositoryImpl(BaseRepositoryImpl[Politician], PoliticianRepository):
    """Implementation of politician repository using SQLAlchemy."""

    def __init__(
        self,
        session: AsyncSession | Session,
        model_class: type[Any] | None = None,
    ):
        """Initialize repository.

        Args:
            session: Database session (async or sync)
            model_class: Optional model class for compatibility
        """
        # Use dynamic model if no model class provided
        if model_class is None:
            model_class = PoliticianModel

        # Handle both async and sync sessions
        if isinstance(session, AsyncSession):
            super().__init__(session, Politician, model_class)
            self.sync_session = None
            self.async_session = session
        else:
            # For sync session, create a wrapper
            self.sync_session = session
            self.async_session = None
            self.session = session
            self.entity_class = Politician
            self.model_class = model_class

        # Initialize legacy repository for sync operations
        self.legacy_repo = None
        if self.sync_session:
            from src.models.politician import Politician as PoliticianPydanticModel

            self.legacy_repo = TypedRepository(
                PoliticianPydanticModel,
                "politicians",
                use_session=True,
                session=self.sync_session,
            )

    async def get_by_name_and_party(
        self, name: str, political_party_id: int | None = None
    ) -> Politician | None:
        """Get politician by name and political party."""
        if self.async_session:
            conditions = ["name = :name"]
            params: dict[str, SQLParam] = {"name": name}

            if political_party_id is not None:
                conditions.append("political_party_id = :party_id")
                params["party_id"] = political_party_id

            query = text(f"""
                SELECT * FROM politicians
                WHERE {" AND ".join(conditions)}
                LIMIT 1
            """)
            result = await self.async_session.execute(query, params)
            row = result.fetchone()
            return self._row_to_entity(row) if row else None
        else:
            # Sync implementation
            if not self.sync_session:
                return None
            conditions = ["name = :name"]
            params: dict[str, SQLParam] = {"name": name}

            if political_party_id is not None:
                conditions.append("political_party_id = :party_id")
                params["party_id"] = political_party_id

            query = text(f"""
                SELECT * FROM politicians
                WHERE {" AND ".join(conditions)}
                LIMIT 1
            """)
            result = self.sync_session.execute(query, params)
            row = result.fetchone()
            return self._row_to_entity(row) if row else None

    async def get_by_speaker_id(self, speaker_id: int) -> Politician | None:
        """Get politician by speaker ID."""
        if self.async_session:
            query = text("""
                SELECT * FROM politicians
                WHERE speaker_id = :speaker_id
                LIMIT 1
            """)
            result = await self.async_session.execute(query, {"speaker_id": speaker_id})
            row = result.fetchone()
            return self._row_to_entity(row) if row else None
        else:
            # Sync implementation
            if not self.sync_session:
                return None
            query = text("""
                SELECT * FROM politicians
                WHERE speaker_id = :speaker_id
                LIMIT 1
            """)
            result = self.sync_session.execute(query, {"speaker_id": speaker_id})
            row = result.fetchone()
            return self._row_to_entity(row) if row else None

    async def get_by_party(self, political_party_id: int) -> list[Politician]:
        """Get all politicians for a political party."""
        if self.async_session:
            query = text("""
                SELECT * FROM politicians
                WHERE political_party_id = :party_id
                ORDER BY name
            """)
            result = await self.async_session.execute(
                query, {"party_id": political_party_id}
            )
            rows = result.fetchall()
            return [self._row_to_entity(row) for row in rows]
        else:
            # Sync implementation
            if not self.sync_session:
                return []
            query = text("""
                SELECT * FROM politicians
                WHERE political_party_id = :party_id
                ORDER BY name
            """)
            result = self.sync_session.execute(query, {"party_id": political_party_id})
            rows = result.fetchall()
            return [self._row_to_entity(row) for row in rows]

    async def search_by_name(self, name_pattern: str) -> list[Politician]:
        """Search politicians by name pattern."""
        if self.async_session:
            query = text("""
                SELECT * FROM politicians
                WHERE name ILIKE :pattern
                ORDER BY name
            """)
            result = await self.async_session.execute(
                query, {"pattern": f"%{name_pattern}%"}
            )
            rows = result.fetchall()
            return [self._row_to_entity(row) for row in rows]
        else:
            # Sync implementation - still return Politician objects
            if not self.sync_session:
                return []

            query = text("""
                SELECT * FROM politicians
                WHERE name ILIKE :pattern
                ORDER BY name
            """)
            result = self.sync_session.execute(query, {"pattern": f"%{name_pattern}%"})
            rows = result.fetchall()

            # Return as Politician objects for consistency
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
                        "position",
                        "prefecture",
                        "electoral_district",
                        "profile_url",
                        "party_position",
                        "speaker_id",
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
                        speaker_id=data.get("speaker_id", 0),  # Provide default value
                        political_party_id=data.get("political_party_id"),
                        position=data.get("position"),
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

        # Commit changes if async
        if self.async_session:
            await self.async_session.commit()
        elif self.sync_session:
            self.sync_session.commit()

        return {"created": created, "updated": updated, "errors": errors}

    async def fetch_as_dict_async(
        self, query: str, params: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        """Execute raw SQL query and return results as dictionaries (async)."""
        if self.async_session:
            result = await self.async_session.execute(text(query), params or {})
            rows = result.fetchall()
            return [dict(row) for row in rows]
        else:
            # Sync implementation
            if not self.sync_session:
                return []
            result = self.sync_session.execute(text(query), params or {})
            rows = result.fetchall()
            return [dict(row) for row in rows]

    def _row_to_entity(self, row: Any) -> Politician:
        """Convert database row to domain entity."""
        if row is None:
            raise ValueError("Cannot convert None to Politician entity")

        # Handle both Row and dict objects
        if hasattr(row, "_mapping"):
            data = dict(getattr(row, "_mapping"))  # noqa: B009
        elif isinstance(row, dict):
            data = row
        else:
            # Try to access as attributes
            data = {
                "id": getattr(row, "id", None),
                "name": getattr(row, "name", None),
                "speaker_id": getattr(row, "speaker_id", None),
                "political_party_id": getattr(row, "political_party_id", None),
                "position": getattr(row, "position", None),
                "prefecture": getattr(row, "prefecture", None),
                "electoral_district": getattr(row, "electoral_district", None),
                "profile_url": getattr(row, "profile_url", None),
                "party_position": getattr(row, "party_position", None),
            }

        return Politician(
            name=str(data.get("name") or ""),
            speaker_id=int(data.get("speaker_id") or 0),
            political_party_id=data.get("political_party_id"),
            furigana=None,  # Not in current database
            position=data.get("position"),
            district=data.get(
                "electoral_district"
            ),  # Map electoral_district to district
            profile_image_url=None,  # Not in current database
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
            speaker_id=entity.speaker_id,
            political_party_id=entity.political_party_id,
            position=entity.position,
            prefecture=None,  # No direct mapping from entity.district
            electoral_district=entity.district,  # Map district to electoral_district
            profile_url=entity.profile_page_url,  # Map profile_page_url to profile_url
            party_position=None,  # Not in entity
        )

    def _update_model(self, model: Any, entity: Politician) -> None:
        """Update model fields from entity."""
        model.name = entity.name
        model.speaker_id = entity.speaker_id
        model.political_party_id = entity.political_party_id
        model.position = entity.position
        model.electoral_district = entity.district
        model.profile_url = entity.profile_page_url

    async def create_entity(self, entity: Politician) -> Politician:
        """Create a new politician entity (async) without committing."""
        # Create without committing (for bulk operations)
        model = self._to_model(entity)

        if self.async_session:
            self.async_session.add(model)
            # Don't commit here - let the caller decide when to commit
            await self.async_session.flush()  # Flush to get the ID without committing
            await self.async_session.refresh(model)
        elif self.sync_session:
            self.sync_session.add(model)
            self.sync_session.flush()
            self.sync_session.refresh(model)

        return self._to_entity(model)

    # Sync wrapper methods for backward compatibility
    def find_by_name_and_party(
        self, name: str, political_party_id: int | None = None
    ) -> Any:
        """Sync wrapper for get_by_name_and_party (backward compatibility)."""
        if self.legacy_repo:
            query = "SELECT * FROM politicians WHERE name = :name"
            params: dict[str, Any] = {"name": name}
            if political_party_id is not None:
                query += " AND political_party_id = :party_id"
                params["party_id"] = political_party_id
            query += " LIMIT 1"
            return self.legacy_repo.fetch_one(query, params)
        return None

    def find_by_name(self, name: str) -> list[Any]:
        """Find politicians by name (for backward compatibility)."""
        # Use the existing search_by_name_sync method
        return self.search_by_name_sync(name)

    def execute_query(
        self, query: str, params: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        """Execute raw SQL query (backward compatibility)."""
        return self.fetch_as_dict_sync(query, params)

    def create_sync(self, politician_create: PoliticianCreate) -> Any:
        """Sync wrapper for create (backward compatibility)."""
        if self.legacy_repo and hasattr(self.legacy_repo, "create"):
            return self.legacy_repo.create(politician_create)  # type: ignore
        return None

    def update_v2(self, politician_id: int, update_data: PoliticianUpdate) -> Any:
        """Sync wrapper for update (backward compatibility)."""
        if self.legacy_repo and hasattr(self.legacy_repo, "update"):
            return self.legacy_repo.update(politician_id, update_data)  # type: ignore
        return None

    def search_by_name_sync(self, name_pattern: str) -> list[dict[str, Any]]:
        """Sync wrapper for search_by_name (backward compatibility)."""
        # This method is for sync code that expects a list of dicts
        if self.sync_session:
            # TODO: Implement sync version or migrate to async
            # Legacy repository has been removed - Issue #430
            return []
        return []

    def bulk_create_politicians_sync(
        self, politicians_data: list[dict[str, Any]]
    ) -> dict[str, list[Any] | list[dict[str, Any]]]:
        """Sync wrapper for bulk_create_politicians (backward compatibility)."""
        # Use the legacy repository's bulk_create_politicians if available
        if self.sync_session:
            # TODO: Implement sync version or migrate to async
            # Legacy repository has been removed - Issue #430
            return {"created": [], "updated": [], "errors": []}
        return {"created": [], "updated": [], "errors": []}

    def close(self) -> None:
        """Close the session if needed."""
        # Sessions are typically managed by the application, not the repository
        # This is here for backward compatibility
        pass

    def fetch_as_dict_sync(
        self, query: str, params: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        """Sync wrapper for fetch_as_dict (backward compatibility)."""
        if self.sync_session:
            result = self.sync_session.execute(text(query), params or {})
            rows = result.fetchall()
            # SQLAlchemy Row objects need special handling
            result_list = []
            for row in rows:
                # Try to convert row to dict using various methods
                try:
                    # Try _mapping with getattr to avoid direct access
                    if hasattr(row, "_mapping"):
                        mapping = getattr(row, "_mapping")  # noqa: B009
                        result_list.append(dict(mapping))
                    elif hasattr(row, "keys"):
                        # SQLAlchemy 1.4 Row object
                        result_list.append(dict(zip(row.keys(), row, strict=False)))
                    else:
                        # Fallback for other row types
                        result_list.append(dict(row))
                except Exception:
                    # Final fallback - try to convert directly
                    try:
                        result_list.append(dict(row))
                    except Exception:
                        # If all else fails, create dict from keys
                        if hasattr(row, "keys"):
                            result_list.append({k: row[k] for k in row.keys()})
                        else:
                            result_list.append({})
            return result_list
        return []

    # Alias for backward compatibility with streamlit code
    fetch_as_dict = fetch_as_dict_sync

    def fetch_all_as_models(
        self,
        model_class: type[Any],
        query: str,
        params: dict[str, Any] | None = None,
    ) -> list[Any]:
        """Fetch all rows as models - wrapper for TypedRepository.fetch_all."""
        if self.legacy_repo and hasattr(self.legacy_repo, "fetch_all"):
            return list(self.legacy_repo.fetch_all(query, params))  # type: ignore
        return []

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
                name, speaker_id, political_party_id,
                position, electoral_district, profile_url
            )
            VALUES (
                :name, :speaker_id, :political_party_id,
                :position, :electoral_district, :profile_url
            )
            RETURNING *
        """)

        params = {
            "name": entity.name,
            "speaker_id": entity.speaker_id,
            "political_party_id": entity.political_party_id,
            "position": entity.position,
            # Map district to electoral_district
            "electoral_district": entity.district,
            # Map profile_page_url to profile_url
            "profile_url": entity.profile_page_url,
        }

        result = await self.session.execute(query, params)
        await self.session.commit()

        row = result.first()
        if row:
            return self._row_to_entity(row)
        raise RuntimeError("Failed to create politician")

    async def update(self, entity: Politician) -> Politician:
        """Update an existing politician."""
        from src.exceptions import UpdateError

        query = text("""
            UPDATE politicians
            SET name = :name,
                speaker_id = :speaker_id,
                political_party_id = :political_party_id,
                position = :position,
                electoral_district = :electoral_district,
                profile_url = :profile_url
            WHERE id = :id
            RETURNING *
        """)

        params = {
            "id": entity.id,
            "name": entity.name,
            "speaker_id": entity.speaker_id,
            "political_party_id": entity.political_party_id,
            "position": entity.position,
            # Map district to electoral_district
            "electoral_district": entity.district,
            # Map profile_page_url to profile_url
            "profile_url": entity.profile_page_url,
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
