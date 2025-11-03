"""Repository interface for data coverage statistics."""

from abc import ABC, abstractmethod

from src.domain.entities.data_coverage_stats import (
    ActivityData,
    GoverningBodyStats,
    MeetingStats,
    SpeakerMatchingStats,
)


class IDataCoverageRepository(ABC):
    """Repository interface for data coverage statistics.

    This repository provides aggregation queries to calculate
    statistics about data coverage across the system.
    """

    @abstractmethod
    async def get_governing_body_stats(self) -> GoverningBodyStats:
        """Get statistics about governing body coverage.

        Returns:
            GoverningBodyStats: Statistics including total governing bodies,
                those with conferences, those with meetings, and coverage percentage.
        """
        pass

    @abstractmethod
    async def get_meeting_stats(self) -> MeetingStats:
        """Get statistics about meetings.

        Returns:
            MeetingStats: Statistics including total meetings, those with minutes,
                those with conversations, and average conversations per meeting.
        """
        pass

    @abstractmethod
    async def get_speaker_matching_stats(self) -> SpeakerMatchingStats:
        """Get statistics about speaker matching.

        Returns:
            SpeakerMatchingStats: Statistics about speaker-politician matching,
                including match rate and conversation linkage rate.
        """
        pass

    @abstractmethod
    async def get_activity_trend(self, period: str = "30d") -> list[ActivityData]:
        """Get activity trend data for a specified period.

        Args:
            period: Period specification (e.g., "7d", "30d", "90d")
                Default is "30d" for 30 days.

        Returns:
            list[ActivityData]: List of daily activity data points.
        """
        pass
