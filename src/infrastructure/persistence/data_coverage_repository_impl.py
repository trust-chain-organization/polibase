"""Implementation of data coverage repository using SQLAlchemy."""

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.data_coverage_stats import (
    ActivityData,
    GoverningBodyStats,
    MeetingStats,
    SpeakerMatchingStats,
)
from src.domain.repositories.data_coverage_repository import IDataCoverageRepository
from src.domain.repositories.session_adapter import ISessionAdapter


class DataCoverageRepositoryImpl(IDataCoverageRepository):
    """Implementation of IDataCoverageRepository using SQLAlchemy.

    This repository provides optimized aggregation queries for
    data coverage statistics using database indexes.
    """

    def __init__(self, session: AsyncSession | ISessionAdapter):
        """Initialize repository with database session.

        Args:
            session: Database session (AsyncSession or ISessionAdapter)
        """
        self.session = session

    async def get_governing_body_stats(self) -> GoverningBodyStats:
        """Get statistics about governing body coverage.

        This query uses JOINs and COUNT DISTINCT to calculate coverage metrics
        efficiently using database indexes on foreign keys.

        Returns:
            GoverningBodyStats: Statistics about governing body coverage
        """
        query = text("""
            WITH stats AS (
                SELECT
                    COUNT(DISTINCT gb.id) as total,
                    COUNT(DISTINCT c.governing_body_id) as with_conferences,
                    COUNT(DISTINCT m_gb.governing_body_id) as with_meetings
                FROM governing_bodies gb
                LEFT JOIN conferences c ON gb.id = c.governing_body_id
                LEFT JOIN (
                    SELECT DISTINCT c2.governing_body_id
                    FROM conferences c2
                    JOIN meetings m ON c2.id = m.conference_id
                ) m_gb ON gb.id = m_gb.governing_body_id
            )
            SELECT
                total,
                with_conferences,
                with_meetings,
                CASE
                    WHEN total > 0
                    THEN ROUND(CAST(with_meetings AS REAL) / total * 100, 2)
                    ELSE 0.0
                END as coverage_percentage
            FROM stats
        """)

        result = await self.session.execute(query)
        row = result.fetchone()

        if not row:
            return {
                "total": 0,
                "with_conferences": 0,
                "with_meetings": 0,
                "coverage_percentage": 0.0,
            }

        return {
            "total": row.total,
            "with_conferences": row.with_conferences,
            "with_meetings": row.with_meetings,
            "coverage_percentage": float(row.coverage_percentage),
        }

    async def get_meeting_stats(self) -> MeetingStats:
        """Get statistics about meetings.

        Uses aggregation and subqueries to calculate meeting statistics
        including minutes and conversations coverage.

        Returns:
            MeetingStats: Statistics about meetings
        """
        # Main statistics query
        stats_query = text("""
            SELECT
                COUNT(DISTINCT m.id) as total_meetings,
                COUNT(DISTINCT mi.meeting_id) as with_minutes,
                COUNT(DISTINCT c.meeting_id) as with_conversations,
                CASE
                    WHEN COUNT(DISTINCT m.id) > 0
                    THEN ROUND(
                        CAST(COUNT(c.id) AS REAL) / COUNT(DISTINCT m.id), 2
                    )
                    ELSE 0.0
                END as avg_conversations
            FROM meetings m
            LEFT JOIN minutes mi ON m.id = mi.meeting_id
            LEFT JOIN conversations c ON m.id = c.meeting_id
        """)

        # Conference breakdown query
        conference_query = text("""
            SELECT
                conf.name,
                COUNT(DISTINCT m.id) as meeting_count
            FROM conferences conf
            LEFT JOIN meetings m ON conf.id = m.conference_id
            GROUP BY conf.id, conf.name
            ORDER BY meeting_count DESC
        """)

        # Execute both queries
        stats_result = await self.session.execute(stats_query)
        stats_row = stats_result.fetchone()

        conference_result = await self.session.execute(conference_query)
        conference_rows = conference_result.fetchall()

        if not stats_row:
            return {
                "total_meetings": 0,
                "with_minutes": 0,
                "with_conversations": 0,
                "average_conversations_per_meeting": 0.0,
                "meetings_by_conference": {},
            }

        # Build conference breakdown dictionary
        meetings_by_conference = {
            row.name: row.meeting_count for row in conference_rows
        }

        return {
            "total_meetings": stats_row.total_meetings,
            "with_minutes": stats_row.with_minutes,
            "with_conversations": stats_row.with_conversations,
            "average_conversations_per_meeting": float(stats_row.avg_conversations),
            "meetings_by_conference": meetings_by_conference,
        }

    async def get_speaker_matching_stats(self) -> SpeakerMatchingStats:
        """Get statistics about speaker matching.

        Calculates matching rates between speakers and politicians,
        and conversation linkage rates.

        Returns:
            SpeakerMatchingStats: Statistics about speaker-politician matching
        """
        query = text("""
            WITH speaker_stats AS (
                SELECT
                    COUNT(DISTINCT s.id) as total_speakers,
                    COUNT(DISTINCT CASE
                        WHEN s.type IN ('politician', '政治家')
                        THEN s.id
                    END) as matched_speakers
                FROM speakers s
            ),
            conversation_stats AS (
                SELECT
                    COUNT(DISTINCT c.id) as total_conversations,
                    COUNT(DISTINCT CASE
                        WHEN c.speaker_id IS NOT NULL
                        THEN c.id
                    END) as linked_conversations
                FROM conversations c
            )
            SELECT
                ss.total_speakers,
                ss.matched_speakers,
                ss.total_speakers - ss.matched_speakers as unmatched_speakers,
                CASE
                    WHEN ss.total_speakers > 0
                    THEN ROUND(
                        CAST(ss.matched_speakers AS REAL)
                        / ss.total_speakers * 100, 2
                    )
                    ELSE 0.0
                END as matching_rate,
                cs.total_conversations,
                cs.linked_conversations,
                CASE
                    WHEN cs.total_conversations > 0
                    THEN ROUND(
                        CAST(cs.linked_conversations AS REAL)
                        / cs.total_conversations * 100, 2
                    )
                    ELSE 0.0
                END as linkage_rate
            FROM speaker_stats ss, conversation_stats cs
        """)

        result = await self.session.execute(query)
        row = result.fetchone()

        if not row:
            return {
                "total_speakers": 0,
                "matched_speakers": 0,
                "unmatched_speakers": 0,
                "matching_rate": 0.0,
                "total_conversations": 0,
                "linked_conversations": 0,
                "linkage_rate": 0.0,
            }

        return {
            "total_speakers": row.total_speakers,
            "matched_speakers": row.matched_speakers,
            "unmatched_speakers": row.unmatched_speakers,
            "matching_rate": float(row.matching_rate),
            "total_conversations": row.total_conversations,
            "linked_conversations": row.linked_conversations,
            "linkage_rate": float(row.linkage_rate),
        }

    async def get_activity_trend(self, period: str = "30d") -> list[ActivityData]:
        """Get activity trend data for a specified period.

        Uses generate_series to create a complete date range and
        LEFT JOINs to ensure all dates are included even with no data.

        Args:
            period: Period specification (e.g., "7d", "30d", "90d")

        Returns:
            list[ActivityData]: List of daily activity data points

        Raises:
            ValueError: If period format is invalid
        """
        # Parse period string (e.g., "30d" -> 30 days)
        if not period.endswith("d"):
            raise ValueError("Period must end with 'd' (e.g., '30d')")

        try:
            days = int(period[:-1])
        except ValueError as err:
            raise ValueError(
                "Period must be a number followed by 'd' (e.g., '30d')"
            ) from err

        if days <= 0 or days > 365:
            raise ValueError("Period must be between 1 and 365 days")

        # Query with optimized date series and aggregations
        query = text(f"""
            WITH date_series AS (
                SELECT generate_series(
                    CURRENT_DATE - INTERVAL '{days} days',
                    CURRENT_DATE,
                    '1 day'::interval
                )::date as date
            ),
            daily_meetings AS (
                SELECT
                    DATE(date) as date,
                    COUNT(*) as count
                FROM meetings
                WHERE date >= CURRENT_DATE - INTERVAL '{days} days'
                    AND date <= CURRENT_DATE
                GROUP BY DATE(date)
            ),
            daily_conversations AS (
                SELECT
                    DATE(m.date) as date,
                    COUNT(c.id) as count
                FROM conversations c
                JOIN meetings m ON c.meeting_id = m.id
                WHERE m.date >= CURRENT_DATE - INTERVAL '{days} days'
                    AND m.date <= CURRENT_DATE
                GROUP BY DATE(m.date)
            ),
            daily_speakers AS (
                SELECT
                    DATE(created_at) as date,
                    COUNT(*) as count
                FROM speakers
                WHERE created_at >= CURRENT_DATE - INTERVAL '{days} days'
                    AND created_at <= CURRENT_DATE
                GROUP BY DATE(created_at)
            ),
            daily_politicians AS (
                SELECT
                    DATE(created_at) as date,
                    COUNT(*) as count
                FROM politicians
                WHERE created_at >= CURRENT_DATE - INTERVAL '{days} days'
                    AND created_at <= CURRENT_DATE
                GROUP BY DATE(created_at)
            )
            SELECT
                ds.date,
                COALESCE(dm.count, 0) as meetings_count,
                COALESCE(dc.count, 0) as conversations_count,
                COALESCE(dsp.count, 0) as speakers_count,
                COALESCE(dp.count, 0) as politicians_count
            FROM date_series ds
            LEFT JOIN daily_meetings dm ON ds.date = dm.date
            LEFT JOIN daily_conversations dc ON ds.date = dc.date
            LEFT JOIN daily_speakers dsp ON ds.date = dsp.date
            LEFT JOIN daily_politicians dp ON ds.date = dp.date
            ORDER BY ds.date
        """)

        result = await self.session.execute(query)
        rows = result.fetchall()

        activity_data: list[ActivityData] = []
        for row in rows:
            activity_data.append(
                {
                    "date": row.date.isoformat(),
                    "meetings_count": row.meetings_count,
                    "conversations_count": row.conversations_count,
                    "speakers_count": row.speakers_count,
                    "politicians_count": row.politicians_count,
                }
            )

        return activity_data
