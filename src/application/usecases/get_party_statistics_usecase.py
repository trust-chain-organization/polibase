"""Use case for getting party statistics."""

from typing import TypedDict

from src.domain.repositories.extracted_politician_repository import (
    ExtractedPoliticianRepository,
)
from src.domain.repositories.political_party_repository import PoliticalPartyRepository
from src.domain.repositories.politician_repository import PoliticianRepository


class PartyStatisticsDTO(TypedDict):
    """DTO for party statistics."""

    party_id: int
    party_name: str
    extracted_total: int
    extracted_pending: int
    extracted_reviewed: int
    extracted_approved: int
    extracted_rejected: int
    extracted_converted: int
    politicians_total: int


class GetPartyStatisticsUseCase:
    """Use case for retrieving party statistics."""

    def __init__(
        self,
        political_party_repo: PoliticalPartyRepository,
        extracted_politician_repo: ExtractedPoliticianRepository,
        politician_repo: PoliticianRepository,
    ):
        """Initialize the use case.

        Args:
            political_party_repo: Political party repository
            extracted_politician_repo: Extracted politician repository
            politician_repo: Politician repository
        """
        self.political_party_repo = political_party_repo
        self.extracted_politician_repo = extracted_politician_repo
        self.politician_repo = politician_repo

    async def execute(self) -> list[PartyStatisticsDTO]:
        """Get statistics for all parties.

        Returns:
            List of party statistics
        """
        # Get all political parties
        parties = await self.political_party_repo.get_all()

        statistics: list[PartyStatisticsDTO] = []
        for party in parties:
            if party.id is None:
                continue

            # Get extracted politician statistics
            extracted_stats = (
                await self.extracted_politician_repo.get_statistics_by_party(party.id)
            )

            # Get politician count
            politician_count = await self.politician_repo.count_by_party(party.id)

            # Build statistics DTO
            party_stats: PartyStatisticsDTO = {
                "party_id": party.id,
                "party_name": party.name,
                "extracted_total": extracted_stats.get("total", 0),
                "extracted_pending": extracted_stats.get("pending", 0),
                "extracted_reviewed": extracted_stats.get("reviewed", 0),
                "extracted_approved": extracted_stats.get("approved", 0),
                "extracted_rejected": extracted_stats.get("rejected", 0),
                "extracted_converted": extracted_stats.get("converted", 0),
                "politicians_total": politician_count,
            }
            statistics.append(party_stats)

        # Sort by party name
        statistics.sort(key=lambda x: x["party_name"])

        return statistics

    async def execute_by_id(self, party_id: int) -> PartyStatisticsDTO | None:
        """Get statistics for a specific party.

        Args:
            party_id: Political party ID

        Returns:
            Party statistics or None if not found
        """
        # Get the party
        party = await self.political_party_repo.get_by_id(party_id)
        if not party:
            return None

        # Get extracted politician statistics
        extracted_stats = await self.extracted_politician_repo.get_statistics_by_party(
            party_id
        )

        # Get politician count
        politician_count = await self.politician_repo.count_by_party(party_id)

        # Build statistics DTO
        if party.id is None:
            return None

        party_stats: PartyStatisticsDTO = {
            "party_id": party.id,
            "party_name": party.name,
            "extracted_total": extracted_stats.get("total", 0),
            "extracted_pending": extracted_stats.get("pending", 0),
            "extracted_reviewed": extracted_stats.get("reviewed", 0),
            "extracted_approved": extracted_stats.get("approved", 0),
            "extracted_rejected": extracted_stats.get("rejected", 0),
            "extracted_converted": extracted_stats.get("converted", 0),
            "politicians_total": politician_count,
        }

        return party_stats
