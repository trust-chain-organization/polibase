"""DTOs for data coverage use cases."""

from typing import TypedDict


class ViewActivityTrendInputDTO(TypedDict):
    """Input DTO for viewing activity trend.

    Attributes:
        period: Period specification (e.g., "7d", "30d", "90d").
            Default is "30d" for 30 days.
    """

    period: str


class GoverningBodyCoverageOutputDTO(TypedDict):
    """Output DTO for governing body coverage statistics.

    Attributes:
        total: Total number of governing bodies
        with_conferences: Number of governing bodies with conferences
        with_meetings: Number of governing bodies with meetings
        coverage_percentage: Percentage of governing bodies with data
    """

    total: int
    with_conferences: int
    with_meetings: int
    coverage_percentage: float


class MeetingCoverageOutputDTO(TypedDict):
    """Output DTO for meeting coverage statistics.

    Attributes:
        total_meetings: Total number of meetings
        with_minutes: Number of meetings with minutes
        with_conversations: Number of meetings with conversations
        average_conversations_per_meeting: Average conversations per meeting
        meetings_by_conference: Breakdown by conference
    """

    total_meetings: int
    with_minutes: int
    with_conversations: int
    average_conversations_per_meeting: float
    meetings_by_conference: dict[str, int]


class SpeakerMatchingStatsOutputDTO(TypedDict):
    """Output DTO for speaker matching statistics.

    Attributes:
        total_speakers: Total number of speakers
        matched_speakers: Number of speakers matched to politicians
        unmatched_speakers: Number of unmatched speakers
        matching_rate: Percentage of matched speakers
        total_conversations: Total number of conversations
        linked_conversations: Number of conversations linked to speakers
        linkage_rate: Percentage of linked conversations
    """

    total_speakers: int
    matched_speakers: int
    unmatched_speakers: int
    matching_rate: float
    total_conversations: int
    linked_conversations: int
    linkage_rate: float


class ActivityTrendDataDTO(TypedDict):
    """DTO for activity data for a specific time period.

    Attributes:
        date: Date in ISO format (YYYY-MM-DD)
        meetings_count: Number of meetings on this date
        conversations_count: Number of conversations on this date
        speakers_count: Number of speakers added on this date
        politicians_count: Number of politicians added on this date
    """

    date: str
    meetings_count: int
    conversations_count: int
    speakers_count: int
    politicians_count: int
