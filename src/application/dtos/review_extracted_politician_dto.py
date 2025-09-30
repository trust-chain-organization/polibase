"""DTOs for reviewing extracted politicians."""

from dataclasses import dataclass
from datetime import datetime


@dataclass
class ReviewExtractedPoliticianInputDTO:
    """Input DTO for reviewing a single extracted politician.

    Attributes:
        politician_id: ID of the extracted politician to review
        action: Review action ('approve', 'reject', 'review')
        reviewer_id: ID of the reviewer (optional, defaults to 1)
    """

    politician_id: int
    action: str
    reviewer_id: int = 1


@dataclass
class ReviewExtractedPoliticianOutputDTO:
    """Output DTO for reviewing a single extracted politician.

    Attributes:
        success: Whether the review was successful
        politician_id: ID of the reviewed politician
        name: Name of the politician
        new_status: New status after review
        message: Result message
    """

    success: bool
    politician_id: int
    name: str
    new_status: str
    message: str


@dataclass
class BulkReviewInputDTO:
    """Input DTO for bulk reviewing extracted politicians.

    Attributes:
        politician_ids: List of politician IDs to review
        action: Review action ('approve', 'reject', 'review')
        reviewer_id: ID of the reviewer (optional, defaults to 1)
    """

    politician_ids: list[int]
    action: str
    reviewer_id: int = 1


@dataclass
class BulkReviewOutputDTO:
    """Output DTO for bulk reviewing extracted politicians.

    Attributes:
        total_processed: Total number of politicians processed
        successful_count: Number of successfully reviewed politicians
        failed_count: Number of failed reviews
        results: List of individual review results
        message: Overall result message
    """

    total_processed: int
    successful_count: int
    failed_count: int
    results: list[ReviewExtractedPoliticianOutputDTO]
    message: str


@dataclass
class ExtractedPoliticianFilterDTO:
    """DTO for filtering extracted politicians.

    Attributes:
        statuses: List of statuses to filter by
        party_id: Party ID to filter by
        start_date: Start date for extraction date filter
        end_date: End date for extraction date filter
        search_name: Name search term
        limit: Maximum number of records to return
        offset: Number of records to skip
    """

    statuses: list[str] | None = None
    party_id: int | None = None
    start_date: datetime | None = None
    end_date: datetime | None = None
    search_name: str | None = None
    limit: int = 100
    offset: int = 0


@dataclass
class ExtractedPoliticianStatisticsDTO:
    """DTO for extracted politician statistics.

    Attributes:
        total: Total number of extracted politicians
        pending_count: Number of pending reviews
        reviewed_count: Number of reviewed politicians
        approved_count: Number of approved politicians
        rejected_count: Number of rejected politicians
        converted_count: Number of converted politicians
        party_statistics: Statistics by party
    """

    total: int
    pending_count: int
    reviewed_count: int
    approved_count: int
    rejected_count: int
    converted_count: int
    party_statistics: dict[str, dict[str, int]]


@dataclass
class UpdateExtractedPoliticianInputDTO:
    """Input DTO for updating an extracted politician.

    Attributes:
        politician_id: ID of the politician to update
        name: Updated name
        party_id: Updated party ID
        district: Updated district
        profile_url: Updated profile URL
    """

    politician_id: int
    name: str
    party_id: int | None = None
    district: str | None = None
    profile_url: str | None = None


@dataclass
class UpdateExtractedPoliticianOutputDTO:
    """Output DTO for updating an extracted politician.

    Attributes:
        success: Whether the update was successful
        politician_id: ID of the updated politician
        message: Result message
    """

    success: bool
    politician_id: int
    message: str
