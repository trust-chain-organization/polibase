"""Meeting repository implementation."""

import logging
from datetime import date
from typing import Any

from sqlalchemy import and_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from src.domain.entities.meeting import Meeting
from src.domain.repositories.meeting_repository import MeetingRepository
from src.infrastructure.persistence.base_repository_impl import BaseRepositoryImpl

logger = logging.getLogger(__name__)


class MeetingRepositoryImpl(BaseRepositoryImpl[Meeting], MeetingRepository):
    """Meeting repository implementation."""

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
            # Define MeetingModel inline to avoid circular imports
            class MeetingModel:
                """Meeting database model (dynamic)."""

                def __init__(self, **kwargs: Any):
                    for key, value in kwargs.items():
                        setattr(self, key, value)

            model_class = MeetingModel

        # Handle both async and sync sessions
        if isinstance(session, AsyncSession):
            super().__init__(session, Meeting, model_class)
            self.sync_session = None
            self.async_session = session
        else:
            # For sync session, create a wrapper
            self.sync_session = session
            self.async_session = None
            self.session = session
            self.entity_class = Meeting
            self.model_class = model_class

        self.legacy_repo = None

        # Initialize legacy repository if sync session is provided
        if self.sync_session:
            from src.database.typed_repository import TypedRepository

            # Use the dynamic model class for legacy repo too
            self.legacy_repo = TypedRepository(
                self.model_class,
                "meetings",
                use_session=True,
                session=self.sync_session,  # type: ignore
            )

    async def get_by_conference_and_date(
        self, conference_id: int, meeting_date: date
    ) -> Meeting | None:
        """Get meeting by conference and date."""
        if self.async_session:
            query = select(self.model_class).where(
                and_(
                    self.model_class.conference_id == conference_id,
                    self.model_class.date == meeting_date,
                )
            )
            result = await self.async_session.execute(query)
            model = result.scalar_one_or_none()
            return self._to_entity(model) if model else None
        else:
            # Use legacy repository for sync session
            if self.legacy_repo:
                meetings = self.legacy_repo.get_meetings(  # type: ignore
                    conference_id=conference_id, limit=100
                )
                for meeting_dict in meetings:
                    if meeting_dict.get("date") == meeting_date:
                        return self._dict_to_entity(meeting_dict)
            return None

    async def get_by_conference(
        self, conference_id: int, limit: int | None = None
    ) -> list[Meeting]:
        """Get all meetings for a conference."""
        if self.async_session:
            query = select(self.model_class).where(
                self.model_class.conference_id == conference_id
            )
            if limit:
                query = query.limit(limit)
            query = query.order_by(self.model_class.date.desc())
            result = await self.async_session.execute(query)
            models = result.scalars().all()
            return [self._to_entity(model) for model in models]
        else:
            # Use raw SQL for sync session
            if self.sync_session:
                from sqlalchemy import text

                sql = "SELECT * FROM meetings WHERE conference_id = :conference_id"
                params = {"conference_id": conference_id}
                if limit:
                    sql += " LIMIT :limit"
                    params["limit"] = limit
                result = self.sync_session.execute(text(sql), params)
                meetings = []
                for row in result:
                    meeting_dict = dict(row._mapping)  # type: ignore
                    meetings.append(self._dict_to_entity(meeting_dict))
                return meetings
            return []

    async def get_unprocessed(self, limit: int | None = None) -> list[Meeting]:
        """Get meetings that haven't been processed yet.

        A meeting is considered unprocessed if it has no associated minutes.
        """
        if self.async_session:
            # Subquery to find meetings with minutes
            from sqlalchemy import exists, text

            subquery = (
                select(text("1"))
                .select_from(text("minutes"))
                .where(text("minutes.meeting_id = meetings.id"))
            )

            query = select(self.model_class).where(~exists(subquery))
            if limit:
                query = query.limit(limit)
            query = query.order_by(self.model_class.date.desc())
            result = await self.async_session.execute(query)
            models = result.scalars().all()
            return [self._to_entity(model) for model in models]
        else:
            # Use raw SQL for sync session
            if self.sync_session:
                from sqlalchemy import text

                sql = """
                SELECT m.* FROM meetings m
                LEFT JOIN minutes min ON m.id = min.meeting_id
                WHERE min.id IS NULL
                ORDER BY m.date DESC
                """
                if limit:
                    sql += f" LIMIT {limit}"
                result = self.sync_session.execute(text(sql))
                meetings = []
                for row in result:
                    meeting_dict = dict(row._mapping)  # type: ignore
                    meetings.append(self._dict_to_entity(meeting_dict))
                return meetings
            return []

    async def update_gcs_uris(
        self,
        meeting_id: int,
        pdf_uri: str | None = None,
        text_uri: str | None = None,
    ) -> bool:
        """Update GCS URIs for a meeting."""
        if self.async_session:
            update_data = {}
            if pdf_uri is not None:
                update_data["gcs_pdf_uri"] = pdf_uri
            if text_uri is not None:
                update_data["gcs_text_uri"] = text_uri

            if not update_data:
                return False

            stmt = (
                update(self.model_class)
                .where(self.model_class.id == meeting_id)
                .values(**update_data)
            )
            result = await self.async_session.execute(stmt)
            await self.async_session.commit()
            return result.rowcount > 0
        else:
            # Use raw SQL for sync session
            if self.sync_session:
                from sqlalchemy import text

                update_parts = []
                params: dict[str, Any] = {"meeting_id": meeting_id}
                if pdf_uri is not None:
                    update_parts.append("gcs_pdf_uri = :pdf_uri")
                    params["pdf_uri"] = pdf_uri
                if text_uri is not None:
                    update_parts.append("gcs_text_uri = :text_uri")
                    params["text_uri"] = text_uri
                if not update_parts:
                    return False
                sql = (
                    f"UPDATE meetings SET {', '.join(update_parts)} "
                    "WHERE id = :meeting_id"
                )
                result = self.sync_session.execute(text(sql), params)
                self.sync_session.commit()
                return getattr(result, "rowcount", 0) > 0  # type: ignore
            return False

    async def update_meeting_gcs_uris(
        self,
        meeting_id: int,
        pdf_uri: str | None = None,
        text_uri: str | None = None,
    ) -> bool:
        """Update GCS URIs for a meeting (backward compatibility alias)."""
        return await self.update_gcs_uris(meeting_id, pdf_uri, text_uri)

    async def get_meetings_with_filters(
        self,
        conference_id: int | None = None,
        governing_body_id: int | None = None,
        offset: int = 0,
        limit: int = 10,
    ) -> tuple[list[dict[str, Any]], int]:
        """Get meetings with filters and pagination."""
        if self.async_session:
            # Build the base query with joins
            base_query = """
            SELECT
                m.id,
                m.conference_id,
                m.date,
                m.url,
                m.name,
                m.gcs_pdf_uri,
                m.gcs_text_uri,
                m.created_at,
                m.updated_at,
                c.name AS conference_name,
                gb.name AS governing_body_name,
                gb.type AS governing_body_type
            FROM meetings m
            JOIN conferences c ON m.conference_id = c.id
            JOIN governing_bodies gb ON c.governing_body_id = gb.id
            WHERE 1=1
            """

            count_query = """
            SELECT COUNT(*)
            FROM meetings m
            JOIN conferences c ON m.conference_id = c.id
            JOIN governing_bodies gb ON c.governing_body_id = gb.id
            WHERE 1=1
            """

            params = {}

            if conference_id:
                base_query += " AND m.conference_id = :conference_id"
                count_query += " AND m.conference_id = :conference_id"
                params["conference_id"] = conference_id

            if governing_body_id:
                base_query += " AND gb.id = :governing_body_id"
                count_query += " AND gb.id = :governing_body_id"
                params["governing_body_id"] = governing_body_id

            base_query += " ORDER BY m.date DESC, m.id DESC"
            base_query += " LIMIT :limit OFFSET :offset"
            params["limit"] = limit
            params["offset"] = offset

            # Execute queries
            from sqlalchemy import text

            result = await self.async_session.execute(text(base_query), params)
            meetings = [dict(row._mapping) for row in result]  # type: ignore

            count_result = await self.async_session.execute(text(count_query), params)
            total_count = count_result.scalar() or 0

            return meetings, total_count
        else:
            # Use raw SQL for sync session
            if self.sync_session:
                from sqlalchemy import text

                base_query = """
                SELECT
                    m.id,
                    m.conference_id,
                    m.date,
                    m.url,
                    m.name,
                    m.gcs_pdf_uri,
                    m.gcs_text_uri,
                    m.created_at,
                    m.updated_at,
                    c.name AS conference_name,
                    gb.name AS governing_body_name,
                    gb.type AS governing_body_type
                FROM meetings m
                JOIN conferences c ON m.conference_id = c.id
                JOIN governing_bodies gb ON c.governing_body_id = gb.id
                WHERE 1=1
                """

                params = {}
                if conference_id:
                    base_query += " AND m.conference_id = :conference_id"
                    params["conference_id"] = conference_id
                if governing_body_id:
                    base_query += " AND gb.id = :governing_body_id"
                    params["governing_body_id"] = governing_body_id

                base_query += " ORDER BY m.date DESC, m.id DESC"
                base_query += " LIMIT :limit OFFSET :offset"
                params["limit"] = limit
                params["offset"] = offset

                result = self.sync_session.execute(text(base_query), params)
                meetings = [dict(row._mapping) for row in result]  # type: ignore
                # Count total
                count_query = """
                SELECT COUNT(*)
                FROM meetings m
                JOIN conferences c ON m.conference_id = c.id
                WHERE 1=1
                """
                params = {}
                if conference_id:
                    count_query += " AND m.conference_id = :conference_id"
                    params["conference_id"] = conference_id
                if governing_body_id:
                    count_query += " AND c.governing_body_id = :governing_body_id"
                    params["governing_body_id"] = governing_body_id

                from sqlalchemy import text

                count_result = self.sync_session.execute(text(count_query), params)  # type: ignore
                total_count = count_result.scalar() or 0

                return meetings, total_count
            return [], 0

    async def get_meeting_by_id_with_info(
        self, meeting_id: int
    ) -> dict[str, Any] | None:
        """Get meeting by ID with conference and governing body info."""
        if self.async_session:
            query = """
            SELECT
                m.id,
                m.conference_id,
                m.date,
                m.url,
                m.name,
                m.gcs_pdf_uri,
                m.gcs_text_uri,
                m.created_at,
                m.updated_at,
                c.name AS conference_name,
                gb.name AS governing_body_name,
                gb.type AS governing_body_type
            FROM meetings m
            JOIN conferences c ON m.conference_id = c.id
            JOIN governing_bodies gb ON c.governing_body_id = gb.id
            WHERE m.id = :meeting_id
            """
            from sqlalchemy import text

            result = await self.async_session.execute(
                text(query), {"meeting_id": meeting_id}
            )
            row = result.first()
            return dict(row._mapping) if row else None  # type: ignore
        else:
            # Use raw SQL for sync session
            if self.sync_session:
                from sqlalchemy import text

                query = """
                SELECT
                    m.id,
                    m.conference_id,
                    m.date,
                    m.url,
                    m.name,
                    m.gcs_pdf_uri,
                    m.gcs_text_uri,
                    m.created_at,
                    m.updated_at,
                    c.name AS conference_name,
                    gb.name AS governing_body_name,
                    gb.type AS governing_body_type
                FROM meetings m
                JOIN conferences c ON m.conference_id = c.id
                JOIN governing_bodies gb ON c.governing_body_id = gb.id
                WHERE m.id = :meeting_id
                """
                result = self.sync_session.execute(
                    text(query), {"meeting_id": meeting_id}
                )
                row = result.first()
                return dict(row._mapping) if row else None  # type: ignore
            return None

    # Override base methods to handle both async and sync
    async def create(self, entity: Meeting) -> Meeting:
        """Create a new meeting."""
        if self.async_session:
            # Use raw SQL for async session to avoid model_class issues
            from datetime import datetime
            from sqlalchemy import text

            sql = """
            INSERT INTO meetings (
                conference_id, date, url, name,
                gcs_pdf_uri, gcs_text_uri, created_at, updated_at
            )
            VALUES (
                :conference_id, :date, :url, :name,
                :gcs_pdf_uri, :gcs_text_uri, :created_at, :updated_at
            )
            RETURNING *
            """
            params = {
                "conference_id": entity.conference_id,
                "date": entity.date or date.today(),
                "url": entity.url or "",
                "name": entity.name,
                "gcs_pdf_uri": entity.gcs_pdf_uri,
                "gcs_text_uri": entity.gcs_text_uri,
                "created_at": datetime.now(),
                "updated_at": datetime.now(),
            }
            result = await self.async_session.execute(text(sql), params)
            await self.async_session.commit()
            row = result.first()
            if row:
                return self._dict_to_entity(dict(row._mapping))  # type: ignore
            raise RuntimeError("Failed to create meeting")
        else:
            # Use raw SQL for sync session
            if self.sync_session:
                from datetime import datetime

                from sqlalchemy import text

                sql = """
                INSERT INTO meetings (
                    conference_id, date, url, name,
                    gcs_pdf_uri, gcs_text_uri, created_at, updated_at
                )
                VALUES (
                    :conference_id, :date, :url, :name,
                    :gcs_pdf_uri, :gcs_text_uri, :created_at, :updated_at
                )
                RETURNING *
                """
                params = {
                    "conference_id": entity.conference_id,
                    "date": entity.date or date.today(),
                    "url": entity.url or "",
                    "name": entity.name,
                    "gcs_pdf_uri": entity.gcs_pdf_uri,
                    "gcs_text_uri": entity.gcs_text_uri,
                    "created_at": datetime.now(),
                    "updated_at": datetime.now(),
                }
                result = self.sync_session.execute(text(sql), params)
                self.sync_session.commit()
                row = result.first()
                if row:
                    return self._dict_to_entity(dict(row._mapping))  # type: ignore
            raise RuntimeError("No session available")

    async def update(self, entity: Meeting) -> Meeting:
        """Update a meeting."""
        if self.async_session:
            # Use raw SQL for async session to avoid model_class issues
            from datetime import datetime
            from sqlalchemy import text

            sql = """
            UPDATE meetings
            SET conference_id = :conference_id,
                date = :date,
                url = :url,
                name = :name,
                gcs_pdf_uri = :gcs_pdf_uri,
                gcs_text_uri = :gcs_text_uri,
                updated_at = :updated_at
            WHERE id = :id
            RETURNING *
            """
            params = {
                "id": entity.id,
                "conference_id": entity.conference_id,
                "date": entity.date,
                "url": entity.url,
                "name": entity.name,
                "gcs_pdf_uri": entity.gcs_pdf_uri,
                "gcs_text_uri": entity.gcs_text_uri,
                "updated_at": datetime.now(),
            }
            result = await self.async_session.execute(text(sql), params)
            await self.async_session.commit()
            row = result.first()
            if row:
                return self._dict_to_entity(dict(row._mapping))  # type: ignore
            raise RuntimeError("Failed to update meeting")
        else:
            # Use raw SQL for sync session
            if self.sync_session and entity.id:
                from datetime import datetime

                from sqlalchemy import text

                sql = """
                UPDATE meetings
                SET conference_id = :conference_id,
                    date = :date,
                    url = :url,
                    name = :name,
                    gcs_pdf_uri = :gcs_pdf_uri,
                    gcs_text_uri = :gcs_text_uri,
                    updated_at = :updated_at
                WHERE id = :id
                RETURNING *
                """
                params = {
                    "id": entity.id,
                    "conference_id": entity.conference_id,
                    "date": entity.date,
                    "url": entity.url,
                    "name": entity.name,
                    "gcs_pdf_uri": entity.gcs_pdf_uri,
                    "gcs_text_uri": entity.gcs_text_uri,
                    "updated_at": datetime.now(),
                }
                result = self.sync_session.execute(text(sql), params)
                self.sync_session.commit()
                row = result.first()
                if row:
                    return self._dict_to_entity(dict(row._mapping))  # type: ignore
            raise RuntimeError("Failed to update meeting")

    async def delete(self, entity_id: int) -> bool:
        """Delete a meeting."""
        if self.async_session:
            # Use raw SQL for async session to avoid model_class issues
            from sqlalchemy import text

            # First check if there are related minutes
            check_sql = (
                "SELECT COUNT(*) FROM minutes WHERE meeting_id = :meeting_id"
            )
            result = await self.async_session.execute(
                text(check_sql), {"meeting_id": entity_id}
            )
            count = result.scalar()
            if count and count > 0:
                return False

            sql = "DELETE FROM meetings WHERE id = :id"
            result = await self.async_session.execute(text(sql), {"id": entity_id})
            await self.async_session.commit()
            return getattr(result, "rowcount", 0) > 0  # type: ignore
        else:
            # Use raw SQL for sync session
            if self.sync_session:
                from sqlalchemy import text

                # First check if there are related minutes
                check_sql = (
                    "SELECT COUNT(*) FROM minutes WHERE meeting_id = :meeting_id"
                )
                result = self.sync_session.execute(
                    text(check_sql), {"meeting_id": entity_id}
                )
                count = result.scalar()
                if count and count > 0:
                    return False

                sql = "DELETE FROM meetings WHERE id = :id"
                result = self.sync_session.execute(text(sql), {"id": entity_id})
                self.sync_session.commit()
                return getattr(result, "rowcount", 0) > 0  # type: ignore
            return False

    async def get_by_id(self, entity_id: int) -> Meeting | None:
        """Get meeting by ID."""
        if self.async_session:
            # Use raw SQL for async session to avoid model_class issues
            from sqlalchemy import text

            sql = "SELECT * FROM meetings WHERE id = :id"
            result = await self.async_session.execute(text(sql), {"id": entity_id})
            row = result.first()
            if row:
                return self._dict_to_entity(dict(row._mapping))  # type: ignore
            return None
        else:
            # Use raw SQL for sync session
            if self.sync_session:
                from sqlalchemy import text

                sql = "SELECT * FROM meetings WHERE id = :id"
                result = self.sync_session.execute(text(sql), {"id": entity_id})
                row = result.first()
                if row:
                    return self._dict_to_entity(dict(row._mapping))  # type: ignore
            return None

    async def get_all(
        self, limit: int | None = None, offset: int | None = 0
    ) -> list[Meeting]:
        """Get all meetings."""
        if self.async_session:
            # Use raw SQL for async session to avoid model_class issues
            from sqlalchemy import text

            sql = "SELECT * FROM meetings ORDER BY date DESC"
            params = {}
            if limit:
                sql += " LIMIT :limit"
                params["limit"] = limit
            if offset:
                sql += " OFFSET :offset"
                params["offset"] = offset
            result = await self.async_session.execute(text(sql), params)
            return [self._dict_to_entity(dict(row._mapping)) for row in result]  # type: ignore
        else:
            # Use raw SQL for sync session
            if self.sync_session:
                from sqlalchemy import text

                sql = "SELECT * FROM meetings ORDER BY date DESC"
                params = {}
                if limit:
                    sql += " LIMIT :limit"
                    params["limit"] = limit
                if offset:
                    sql += " OFFSET :offset"
                    params["offset"] = offset
                result = self.sync_session.execute(text(sql), params)
                return [self._dict_to_entity(dict(row._mapping)) for row in result]  # type: ignore
            return []

    # Conversion methods
    def _to_entity(self, model: Any) -> Meeting:
        """Convert database model to domain entity."""
        if model is None:
            raise ValueError("Cannot convert None to Meeting entity")
        return Meeting(
            id=getattr(model, "id", None),
            conference_id=model.conference_id,
            date=getattr(model, "date", None),
            url=getattr(model, "url", None),
            name=getattr(model, "name", None),
            gcs_pdf_uri=getattr(model, "gcs_pdf_uri", None),
            gcs_text_uri=getattr(model, "gcs_text_uri", None),
        )

    def _to_model(self, entity: Meeting) -> Any:
        """Convert domain entity to database model."""
        return self.model_class(
            id=entity.id,
            conference_id=entity.conference_id,
            date=entity.date,
            url=entity.url,
            name=entity.name,
            gcs_pdf_uri=entity.gcs_pdf_uri,
            gcs_text_uri=entity.gcs_text_uri,
        )

    def _update_model(self, model: Any, entity: Meeting) -> None:
        """Update database model from domain entity."""
        model.conference_id = entity.conference_id
        model.date = entity.date
        model.url = entity.url
        model.name = entity.name
        model.gcs_pdf_uri = entity.gcs_pdf_uri
        model.gcs_text_uri = entity.gcs_text_uri

    def _dict_to_entity(self, data: dict[str, Any]) -> Meeting:
        """Convert dictionary to domain entity."""
        return Meeting(
            id=data.get("id"),
            conference_id=data.get("conference_id") or 0,
            date=data.get("date"),
            url=data.get("url"),
            name=data.get("name"),
            gcs_pdf_uri=data.get("gcs_pdf_uri"),
            gcs_text_uri=data.get("gcs_text_uri"),
        )

    def _pydantic_to_entity(self, model: Any) -> Meeting:
        """Convert Pydantic model to domain entity."""
        return Meeting(
            id=getattr(model, "id", None),
            conference_id=model.conference_id,
            date=model.date,
            url=model.url,
            name=model.name,
            gcs_pdf_uri=model.gcs_pdf_uri,
            gcs_text_uri=model.gcs_text_uri,
        )
