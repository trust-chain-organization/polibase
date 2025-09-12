"""DTOs for proposal judge use cases."""

from dataclasses import dataclass
from datetime import datetime


@dataclass
class ExtractProposalJudgesInputDTO:
    """Input DTO for extracting proposal judges from a URL."""

    url: str
    proposal_id: int | None = None
    conference_id: int | None = None
    force: bool = False


@dataclass
class ExtractedJudgeDTO:
    """DTO for extracted judge data."""

    id: int
    proposal_id: int | None
    extracted_name: str
    extracted_party_name: str | None
    extracted_judgment: str
    source_url: str
    matched_politician_id: int | None
    matching_status: str
    confidence_score: float | None
    created_at: datetime
    updated_at: datetime


@dataclass
class ExtractProposalJudgesOutputDTO:
    """Output DTO for extracted proposal judges."""

    proposal_id: int | None
    extracted_count: int
    judges: list[ExtractedJudgeDTO]


@dataclass
class MatchProposalJudgesInputDTO:
    """Input DTO for matching proposal judges with politicians."""

    proposal_id: int | None = None
    judge_ids: list[int] | None = None


@dataclass
class JudgeMatchResultDTO:
    """DTO for judge match result."""

    judge_id: int
    judge_name: str
    judgment: str
    matched_politician_id: int | None
    matched_politician_name: str | None
    confidence_score: float
    matching_status: str
    matching_notes: str


@dataclass
class MatchProposalJudgesOutputDTO:
    """Output DTO for matching proposal judges."""

    matched_count: int
    needs_review_count: int
    no_match_count: int
    results: list[JudgeMatchResultDTO]


@dataclass
class CreateProposalJudgesInputDTO:
    """Input DTO for creating proposal judges from matched data."""

    proposal_id: int | None = None
    judge_ids: list[int] | None = None


@dataclass
class ProposalJudgeDTO:
    """DTO for proposal judge data."""

    id: int
    proposal_id: int
    politician_id: int
    politician_name: str
    judgment: str
    created_at: datetime
    updated_at: datetime


@dataclass
class CreateProposalJudgesOutputDTO:
    """Output DTO for creating proposal judges."""

    created_count: int
    skipped_count: int
    judges: list[ProposalJudgeDTO]


@dataclass
class ExtractedJudgeUpdateDTO:
    """DTO for updating extracted judge matching status."""

    matched_politician_id: int | None
    matching_status: str
    confidence_score: float
    matching_notes: str | None = None
