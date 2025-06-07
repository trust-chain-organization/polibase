"""Meeting repository for database operations"""

import logging
from datetime import date

from src.database.base_repository import BaseRepository

logger = logging.getLogger(__name__)


class MeetingRepository(BaseRepository):
    """Repository class for Meeting-related database operations"""

    def __init__(self):
        super().__init__(use_session=True)

    def get_governing_bodies(self) -> list[dict]:
        """Get all governing bodies"""
        query = """
        SELECT id, name, type
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
        return self.fetch_as_dict(query)

    def get_conferences_by_governing_body(self, governing_body_id: int) -> list[dict]:
        """Get conferences for a specific governing body"""
        query = """
        SELECT id, name, type
        FROM conferences
        WHERE governing_body_id = :governing_body_id
        ORDER BY name
        """
        return self.fetch_as_dict(query, {"governing_body_id": governing_body_id})

    def get_all_conferences(self) -> list[dict]:
        """Get all conferences with their governing bodies"""
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
        return self.fetch_as_dict(query)

    def get_meetings(
        self, conference_id: int | None = None, limit: int = 100
    ) -> list[dict]:
        """Get meetings, optionally filtered by conference"""
        if conference_id:
            query = """
            SELECT
                m.id,
                m.date,
                m.url,
                c.name as conference_name,
                gb.name as governing_body_name
            FROM meetings m
            JOIN conferences c ON m.conference_id = c.id
            JOIN governing_bodies gb ON c.governing_body_id = gb.id
            WHERE m.conference_id = :conference_id
            ORDER BY m.date DESC
            LIMIT :limit
            """
            params = {"conference_id": conference_id, "limit": limit}
        else:
            query = """
            SELECT
                m.id,
                m.date,
                m.url,
                c.name as conference_name,
                gb.name as governing_body_name
            FROM meetings m
            JOIN conferences c ON m.conference_id = c.id
            JOIN governing_bodies gb ON c.governing_body_id = gb.id
            ORDER BY m.date DESC
            LIMIT :limit
            """
            params = {"limit": limit}

        return self.fetch_as_dict(query, params)

    def create_meeting(self, conference_id: int, meeting_date: date, url: str) -> int:
        """Create a new meeting"""
        return self.insert(
            table="meetings",
            data={"conference_id": conference_id, "date": meeting_date, "url": url},
            returning="id",
        )

    def update_meeting(self, meeting_id: int, meeting_date: date, url: str) -> bool:
        """Update an existing meeting"""
        rows_affected = self.update(
            table="meetings",
            data={"date": meeting_date, "url": url},
            where={"id": meeting_id},
        )
        return rows_affected > 0

    def delete_meeting(self, meeting_id: int) -> bool:
        """Delete a meeting"""
        # First check if there are related minutes
        count = self.count("minutes", {"meeting_id": meeting_id})

        if count > 0:
            logger.warning(
                f"Cannot delete meeting {meeting_id}: has {count} related minutes"
            )
            return False

        rows_affected = self.delete("meetings", {"id": meeting_id})
        return rows_affected > 0

    def get_meeting_by_id(self, meeting_id: int) -> dict | None:
        """Get a specific meeting by ID"""
        query = """
        SELECT
            m.id,
            m.conference_id,
            m.date,
            m.url,
            c.name as conference_name,
            c.governing_body_id,
            gb.name as governing_body_name
        FROM meetings m
        JOIN conferences c ON m.conference_id = c.id
        JOIN governing_bodies gb ON c.governing_body_id = gb.id
        WHERE m.id = :id
        """
        results = self.fetch_as_dict(query, {"id": meeting_id})
        return results[0] if results else None

    # close() method is inherited from BaseRepository
