"""Meeting repository for database operations"""
from typing import List, Dict, Optional
from datetime import date
from sqlalchemy import text
from src.config.database import get_db_session
import logging

logger = logging.getLogger(__name__)


class MeetingRepository:
    """Repository class for Meeting-related database operations"""
    
    def __init__(self):
        self.session = get_db_session()
    
    def get_governing_bodies(self) -> List[Dict]:
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
        result = self.session.execute(text(query))
        return [{"id": row[0], "name": row[1], "type": row[2]} for row in result]
    
    def get_conferences_by_governing_body(self, governing_body_id: int) -> List[Dict]:
        """Get conferences for a specific governing body"""
        query = """
        SELECT id, name, type
        FROM conferences
        WHERE governing_body_id = :governing_body_id
        ORDER BY name
        """
        result = self.session.execute(
            text(query), 
            {"governing_body_id": governing_body_id}
        )
        return [{"id": row[0], "name": row[1], "type": row[2]} for row in result]
    
    def get_meetings(self, conference_id: Optional[int] = None, limit: int = 100) -> List[Dict]:
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
        
        result = self.session.execute(text(query), params)
        return [{
            "id": row[0],
            "date": row[1],
            "url": row[2],
            "conference_name": row[3],
            "governing_body_name": row[4]
        } for row in result]
    
    def create_meeting(self, conference_id: int, meeting_date: date, url: str) -> int:
        """Create a new meeting"""
        query = """
        INSERT INTO meetings (conference_id, date, url)
        VALUES (:conference_id, :date, :url)
        RETURNING id
        """
        result = self.session.execute(
            text(query),
            {
                "conference_id": conference_id,
                "date": meeting_date,
                "url": url
            }
        )
        self.session.commit()
        return result.fetchone()[0]
    
    def update_meeting(self, meeting_id: int, meeting_date: date, url: str) -> bool:
        """Update an existing meeting"""
        query = """
        UPDATE meetings
        SET date = :date, url = :url, updated_at = CURRENT_TIMESTAMP
        WHERE id = :id
        """
        result = self.session.execute(
            text(query),
            {
                "id": meeting_id,
                "date": meeting_date,
                "url": url
            }
        )
        self.session.commit()
        return result.rowcount > 0
    
    def delete_meeting(self, meeting_id: int) -> bool:
        """Delete a meeting"""
        # First check if there are related minutes
        check_query = """
        SELECT COUNT(*) FROM minutes WHERE meeting_id = :meeting_id
        """
        result = self.session.execute(text(check_query), {"meeting_id": meeting_id})
        count = result.fetchone()[0]
        
        if count > 0:
            logger.warning(f"Cannot delete meeting {meeting_id}: has {count} related minutes")
            return False
        
        delete_query = """
        DELETE FROM meetings WHERE id = :id
        """
        result = self.session.execute(text(delete_query), {"id": meeting_id})
        self.session.commit()
        return result.rowcount > 0
    
    def get_meeting_by_id(self, meeting_id: int) -> Optional[Dict]:
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
        result = self.session.execute(text(query), {"id": meeting_id})
        row = result.fetchone()
        if row:
            return {
                "id": row[0],
                "conference_id": row[1],
                "date": row[2],
                "url": row[3],
                "conference_name": row[4],
                "governing_body_id": row[5],
                "governing_body_name": row[6]
            }
        return None
    
    def close(self):
        """Close the database session"""
        self.session.close()