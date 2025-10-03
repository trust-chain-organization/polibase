"""Query service for politician statistics."""

from typing import TypedDict

from src.domain.repositories.politician_repository import PoliticianRepository


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

    def __init__(self, politician_repository: PoliticianRepository):
        """Initialize the query service.

        Args:
            politician_repository: Politician repository
        """
        self.politician_repository = politician_repository

    async def get_party_statistics(self) -> list[PartyStatistics]:
        """Get politician statistics for all parties.

        Returns:
            List of party statistics
        """
        stats_data = await self.politician_repository.get_party_statistics()

        statistics: list[PartyStatistics] = []
        for data in stats_data:
            stat: PartyStatistics = {
                "party_id": data["party_id"],
                "party_name": data["party_name"],
                "extracted_total": data["extracted_total"],
                "extracted_pending": data["extracted_pending"],
                "extracted_reviewed": data["extracted_reviewed"],
                "extracted_approved": data["extracted_approved"],
                "extracted_rejected": data["extracted_rejected"],
                "extracted_converted": data["extracted_converted"],
                "politicians_total": data["politicians_total"],
            }
            statistics.append(stat)

        return statistics

    async def get_party_statistics_by_id(self, party_id: int) -> PartyStatistics | None:
        """Get politician statistics for a specific party.

        Args:
            party_id: Political party ID

        Returns:
            Party statistics or None if not found
        """
        data = await self.politician_repository.get_party_statistics_by_id(party_id)

        if data:
            return {
                "party_id": data["party_id"],
                "party_name": data["party_name"],
                "extracted_total": data["extracted_total"],
                "extracted_pending": data["extracted_pending"],
                "extracted_reviewed": data["extracted_reviewed"],
                "extracted_approved": data["extracted_approved"],
                "extracted_rejected": data["extracted_rejected"],
                "extracted_converted": data["extracted_converted"],
                "politicians_total": data["politicians_total"],
            }

        return None
