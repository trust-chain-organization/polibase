"""Query service for politician statistics."""

from typing import TypedDict

from sqlalchemy import text
from sqlalchemy.engine import Connection


class PartyStatistics(TypedDict):
    """Statistics for a political party."""

    party_id: int
    party_name: str
    # extracted_politicians counts
    extracted_total: int
    extracted_pending: int
    extracted_reviewed: int
    extracted_approved: int
    extracted_rejected: int
    extracted_converted: int
    # politicians count
    politicians_total: int


class PoliticianStatisticsQuery:
    """Query service to retrieve politician statistics."""

    def __init__(self, connection: Connection):
        """Initialize the query service.

        Args:
            connection: Database connection
        """
        self.connection = connection

    def get_party_statistics(self) -> list[PartyStatistics]:
        """Get politician statistics for all parties.

        Returns:
            List of party statistics
        """
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

        result = self.connection.execute(query)
        rows = result.fetchall()

        statistics: list[PartyStatistics] = []
        for row in rows:
            stat: PartyStatistics = {
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
            statistics.append(stat)

        return statistics

    def get_party_statistics_by_id(self, party_id: int) -> PartyStatistics | None:
        """Get politician statistics for a specific party.

        Args:
            party_id: Political party ID

        Returns:
            Party statistics or None if not found
        """
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

        result = self.connection.execute(query, {"party_id": party_id})
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
