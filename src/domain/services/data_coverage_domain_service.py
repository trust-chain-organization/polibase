"""Domain service for data coverage calculations."""

from typing import Any

from src.domain.repositories.conference_repository import ConferenceRepository
from src.domain.repositories.conversation_repository import ConversationRepository
from src.domain.repositories.governing_body_repository import GoverningBodyRepository
from src.domain.repositories.meeting_repository import MeetingRepository
from src.domain.repositories.minutes_repository import MinutesRepository
from src.domain.repositories.politician_repository import PoliticianRepository
from src.domain.repositories.speaker_repository import SpeakerRepository


class DataCoverageDomainService:
    """Domain service for data coverage calculations.

    This service provides business logic for calculating various data coverage metrics
    including governing body coverage, meeting coverage, speaker matching rates, and
    activity statistics.
    """

    def __init__(
        self,
        governing_body_repo: GoverningBodyRepository,
        conference_repo: ConferenceRepository,
        meeting_repo: MeetingRepository,
        minutes_repo: MinutesRepository,
        speaker_repo: SpeakerRepository,
        politician_repo: PoliticianRepository,
        conversation_repo: ConversationRepository,
    ) -> None:
        """Initialize the service with repository dependencies.

        Args:
            governing_body_repo: Repository for governing bodies
            conference_repo: Repository for conferences
            meeting_repo: Repository for meetings
            minutes_repo: Repository for minutes
            speaker_repo: Repository for speakers
            politician_repo: Repository for politicians
            conversation_repo: Repository for conversations
        """
        self._governing_body_repo = governing_body_repo
        self._conference_repo = conference_repo
        self._meeting_repo = meeting_repo
        self._minutes_repo = minutes_repo
        self._speaker_repo = speaker_repo
        self._politician_repo = politician_repo
        self._conversation_repo = conversation_repo

    async def calculate_governing_body_coverage(self) -> dict[str, Any]:
        """Calculate governing body coverage statistics.

        Returns:
            Dictionary containing:
            - total: Total number of municipalities in Japan (1,966)
            - registered: Number of registered governing bodies
            - coverage_rate: Percentage of coverage (registered / total * 100)
        """
        # Japan has 1,966 municipalities (as of the data documentation)
        total_municipalities = 1966

        registered_count = await self._governing_body_repo.count()

        coverage_rate = (
            (registered_count / total_municipalities * 100)
            if total_municipalities > 0
            else 0.0
        )

        return {
            "total": total_municipalities,
            "registered": registered_count,
            "coverage_rate": round(coverage_rate, 2),
        }

    async def calculate_meeting_coverage(self) -> dict[str, Any]:
        """Calculate meeting coverage statistics.

        Returns:
            Dictionary containing:
            - total_governing_bodies: Total registered governing bodies
            - bodies_with_conferences: Number of bodies with at least one conference
            - bodies_with_meetings: Number of bodies with at least one meeting
            - conference_coverage_rate: Percentage of bodies with conferences
            - meeting_coverage_rate: Percentage of bodies with meetings
        """
        total_bodies = await self._governing_body_repo.count()
        bodies_with_conferences = (
            await self._governing_body_repo.count_with_conferences()
        )
        bodies_with_meetings = await self._governing_body_repo.count_with_meetings()

        conference_coverage_rate = (
            (bodies_with_conferences / total_bodies * 100) if total_bodies > 0 else 0.0
        )

        meeting_coverage_rate = (
            (bodies_with_meetings / total_bodies * 100) if total_bodies > 0 else 0.0
        )

        return {
            "total_governing_bodies": total_bodies,
            "bodies_with_conferences": bodies_with_conferences,
            "bodies_with_meetings": bodies_with_meetings,
            "conference_coverage_rate": round(conference_coverage_rate, 2),
            "meeting_coverage_rate": round(meeting_coverage_rate, 2),
        }

    async def calculate_speaker_matching_rate(self) -> dict[str, Any]:
        """Calculate speaker-politician matching rate statistics.

        Returns:
            Dictionary containing:
            - total_speakers: Total number of speakers
            - linked_speakers: Number of speakers linked to politicians
            - overall_matching_rate: Percentage of speakers linked to politicians
            - politician_speakers: Number of speakers marked as politicians
            - linked_politician_speakers: Number of politician speakers linked
            - politician_matching_rate: Percentage of politician speakers linked
        """
        # Get overall speaker-politician statistics
        stats = await self._speaker_repo.get_speaker_politician_stats()

        total_speakers = stats.get("total_speakers", 0)
        linked_speakers = stats.get("linked_speakers", 0)
        politician_speakers = stats.get("politician_speakers", 0)
        linked_politician_speakers = stats.get("linked_politician_speakers", 0)

        overall_matching_rate = (
            (linked_speakers / total_speakers * 100) if total_speakers > 0 else 0.0
        )

        politician_matching_rate = (
            (linked_politician_speakers / politician_speakers * 100)
            if politician_speakers > 0
            else 0.0
        )

        return {
            "total_speakers": total_speakers,
            "linked_speakers": linked_speakers,
            "unlinked_speakers": total_speakers - linked_speakers,
            "overall_matching_rate": round(overall_matching_rate, 2),
            "politician_speakers": politician_speakers,
            "linked_politician_speakers": linked_politician_speakers,
            "unlinked_politician_speakers": politician_speakers
            - linked_politician_speakers,
            "politician_matching_rate": round(politician_matching_rate, 2),
        }

    async def aggregate_activity_statistics(self) -> dict[str, Any]:
        """Aggregate activity statistics.

        Returns:
            Dictionary containing:
            - total_meetings: Total number of meetings
            - total_minutes: Total number of minutes records
            - processed_minutes: Number of processed minutes
            - minutes_processing_rate: Percentage of processed minutes
            - total_conversations: Total number of conversations
            - total_politicians: Total number of politicians
            - total_conferences: Total number of conferences
        """
        total_meetings = await self._meeting_repo.count()
        total_minutes = await self._minutes_repo.count()
        processed_minutes = await self._minutes_repo.count_processed()
        total_conversations = await self._conversation_repo.count()
        total_politicians = await self._politician_repo.count()
        total_conferences = await self._conference_repo.count()

        minutes_processing_rate = (
            (processed_minutes / total_minutes * 100) if total_minutes > 0 else 0.0
        )

        return {
            "total_meetings": total_meetings,
            "total_minutes": total_minutes,
            "processed_minutes": processed_minutes,
            "unprocessed_minutes": total_minutes - processed_minutes,
            "minutes_processing_rate": round(minutes_processing_rate, 2),
            "total_conversations": total_conversations,
            "total_politicians": total_politicians,
            "total_conferences": total_conferences,
        }
