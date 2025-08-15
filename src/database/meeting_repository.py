"""Meeting repository for database operations

This is a legacy wrapper that delegates to the new MeetingRepositoryImpl.
"""

import asyncio
import logging
from datetime import date
from typing import Any

from sqlalchemy.orm import Session

from src.database.typed_repository import TypedRepository
from src.infrastructure.persistence.meeting_repository_impl import MeetingRepositoryImpl
from src.models.meeting_v2 import Meeting, MeetingCreate, MeetingUpdate

logger = logging.getLogger(__name__)


class MeetingRepository(TypedRepository[Meeting]):
    """Repository class for Meeting-related database operations

    This is a legacy wrapper that delegates to the new MeetingRepositoryImpl.
    """

    def __init__(self, session: Session | None = None):
        super().__init__(Meeting, "meetings", use_session=True, session=session)
        # Initialize the new implementation - delay until session is set
        self._impl_initialized = False
        self._impl_session = session

    def _ensure_impl(self):
        """Ensure implementation is initialized with correct session"""
        if not self._impl_initialized:
            self._impl = MeetingRepositoryImpl(session=self.session)
            self._impl_initialized = True

    def _run_async(self, coro: Any) -> Any:
        """Run async method in sync context"""
        loop = None
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            # No running loop
            pass

        if loop and loop.is_running():
            # We're in an async context already
            import threading

            result_container = {}
            exception_container = {}

            def run_in_thread():
                try:
                    new_loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(new_loop)
                    result = new_loop.run_until_complete(coro)
                    result_container["result"] = result
                except Exception as e:
                    exception_container["exception"] = e
                finally:
                    new_loop.close()

            thread = threading.Thread(target=run_in_thread)
            thread.start()
            thread.join()

            if "exception" in exception_container:
                raise exception_container["exception"]
            return result_container.get("result")
        else:
            # No running loop, create one
            return asyncio.run(coro)

    def fetch_as_dict(
        self, query: str, params: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        """Execute query and return results as list of dictionaries"""
        result = self.execute_query(query, params)
        columns = result.keys()
        return [dict(zip(columns, row, strict=False)) for row in result.fetchall()]

    def get_governing_bodies(self) -> list[dict[str, Any]]:
        """Get all governing bodies - DEPRECATED: Use GoverningBodyRepository instead"""
        query = """
        SELECT id, name, type, created_at, updated_at
        FROM governing_bodies
        ORDER BY
            CASE type
                WHEN '国' THEN 1
                WHEN '都道府県' THEN 2
                WHEN '市町村' THEN 3
                ELSE 4
            END,
            name
        """
        # TODO: Move to GoverningBodyRepository
        result = self.execute_query(query)
        columns = result.keys()
        return [dict(zip(columns, row, strict=False)) for row in result.fetchall()]

    def get_conferences_by_governing_body(
        self, governing_body_id: int
    ) -> list[dict[str, Any]]:
        """Get conferences for a specific governing body.

        DEPRECATED: Use ConferenceRepository instead"""
        query = """
        SELECT id, name, type, governing_body_id, created_at, updated_at
        FROM conferences
        WHERE governing_body_id = :governing_body_id
        ORDER BY name
        """
        # TODO: Move to ConferenceRepository
        result = self.execute_query(query, {"governing_body_id": governing_body_id})
        columns = result.keys()
        return [dict(zip(columns, row, strict=False)) for row in result.fetchall()]

    def get_all_conferences(self) -> list[dict[str, Any]]:
        """Get all conferences with their governing bodies.

        DEPRECATED: Use ConferenceRepository instead"""
        query = """
        SELECT
            c.id,
            c.name,
            c.type,
            c.governing_body_id,
            gb.name as governing_body_name,
            gb.type as governing_body_type
        FROM conferences c
        JOIN governing_bodies gb ON c.governing_body_id = gb.id
        ORDER BY gb.type, gb.name, c.name
        """
        # TODO: Move to ConferenceRepository
        result = self.execute_query(query)
        columns = result.keys()
        return [dict(zip(columns, row, strict=False)) for row in result.fetchall()]

    def get_meetings(
        self,
        conference_id: int | None = None,
        governing_body_id: int | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """Get meetings, optionally filtered by conference or governing body"""
        self._ensure_impl()
        meetings, _ = self._run_async(
            self._impl.get_meetings_with_filters(
                conference_id=conference_id,
                governing_body_id=governing_body_id,
                limit=limit,
                offset=offset,
            )
        )
        return meetings

    def create_meeting(
        self,
        conference_id: int,
        meeting_date: date,
        url: str,
        gcs_pdf_uri: str | None = None,
        gcs_text_uri: str | None = None,
    ) -> Meeting:
        """Create a new meeting"""
        meeting = MeetingCreate(
            conference_id=conference_id,
            date=meeting_date,
            url=url,
            name=None,
            gcs_pdf_uri=gcs_pdf_uri,
            gcs_text_uri=gcs_text_uri,
        )
        return self.create_from_model(meeting)

    def update_meeting(
        self,
        meeting_id: int,
        meeting_date: date | None = None,
        url: str | None = None,
        gcs_pdf_uri: str | None = None,
        gcs_text_uri: str | None = None,
    ) -> Meeting | None:
        """Update an existing meeting"""
        update_dict: dict[str, Any] = {}
        if meeting_date is not None:
            update_dict["date"] = meeting_date
        if url is not None:
            update_dict["url"] = url
        if gcs_pdf_uri is not None:
            update_dict["gcs_pdf_uri"] = gcs_pdf_uri
        if gcs_text_uri is not None:
            update_dict["gcs_text_uri"] = gcs_text_uri
        if not update_dict:
            return None

        update_data = MeetingUpdate(**update_dict)
        return self.update_from_model(meeting_id, update_data)

    def delete_meeting(self, meeting_id: int) -> bool:
        """Delete a meeting"""
        # First check if there are related minutes
        # TODO: Use MinutesRepository instead
        query = "SELECT COUNT(*) FROM minutes WHERE meeting_id = :meeting_id"
        result = self.execute_query(query, {"meeting_id": meeting_id})
        count = result.scalar()

        if count and count > 0:
            logger.warning(
                f"Cannot delete meeting {meeting_id}: has {count} related minutes"
            )
            return False

        return self.delete(meeting_id)

    def get_meeting_by_id_with_info(self, meeting_id: int) -> dict[str, Any] | None:
        """Get a specific meeting by ID with conference and governing body info"""
        self._ensure_impl()
        return self._run_async(self._impl.get_meeting_by_id_with_info(meeting_id))

    def get_meeting_by_id(self, meeting_id: int) -> Meeting | None:
        """Get a specific meeting by ID (without join info)"""
        return self.get_by_id(meeting_id)

    def update_meeting_gcs_uris(
        self, meeting_id: int, gcs_pdf_uri: str | None, gcs_text_uri: str | None
    ) -> bool:
        """Update GCS URIs for a meeting"""
        self._ensure_impl()
        return self._run_async(
            self._impl.update_gcs_uris(meeting_id, gcs_pdf_uri, gcs_text_uri)
        )

    def get_unprocessed_meetings(self, limit: int | None = None) -> list[Meeting]:
        """Get meetings that haven't been processed yet"""
        self._ensure_impl()
        meetings = self._run_async(self._impl.get_unprocessed(limit))
        # Convert domain entities to Pydantic models
        return [
            Meeting(
                id=m.id,
                conference_id=m.conference_id,
                date=m.date,
                url=m.url,
                name=m.name,
                gcs_pdf_uri=m.gcs_pdf_uri,
                gcs_text_uri=m.gcs_text_uri,
                created_at=None,  # Will be filled by database
                updated_at=None,  # Will be filled by database
            )
            for m in meetings
        ]

    # close() method is inherited from TypedRepository
