"""DTOs for proposal use cases."""

from dataclasses import dataclass


@dataclass
class ScrapeProposalInputDTO:
    """Input DTO for scraping proposal information."""

    url: str
    meeting_id: int | None = None


@dataclass
class ScrapeProposalOutputDTO:
    """Output DTO for scraped proposal information."""

    content: str
    detail_url: str | None = None
    status_url: str | None = None
    proposal_number: str | None = None
    submission_date: str | None = None  # ISO format date
    summary: str | None = None
    meeting_id: int | None = None


@dataclass
class CreateProposalDTO:
    """DTO for creating a new proposal."""

    content: str
    detail_url: str | None = None
    status_url: str | None = None
    submission_date: str | None = None
    proposal_number: str | None = None
    meeting_id: int | None = None
    summary: str | None = None


@dataclass
class UpdateProposalDTO:
    """DTO for updating an existing proposal."""

    id: int
    content: str | None = None
    detail_url: str | None = None
    status_url: str | None = None
    submission_date: str | None = None
    proposal_number: str | None = None
    meeting_id: int | None = None
    summary: str | None = None


@dataclass
class ProposalDTO:
    """DTO representing a proposal entity."""

    id: int
    content: str
    detail_url: str | None = None
    status_url: str | None = None
    submission_date: str | None = None
    proposal_number: str | None = None
    meeting_id: int | None = None
    summary: str | None = None
