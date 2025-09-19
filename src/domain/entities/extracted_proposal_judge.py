"""ExtractedProposalJudge entity."""

from datetime import datetime
from typing import Any

from src.domain.entities.base import BaseEntity


class ExtractedProposalJudge(BaseEntity):
    """議案賛否抽出情報を表すエンティティ."""

    def __init__(
        self,
        proposal_id: int,
        extracted_politician_name: str | None = None,
        extracted_party_name: str | None = None,
        extracted_parliamentary_group_name: str | None = None,
        extracted_judgment: str | None = None,
        source_url: str | None = None,
        extracted_at: datetime | None = None,
        matched_politician_id: int | None = None,
        matched_parliamentary_group_id: int | None = None,
        matching_confidence: float | None = None,
        matching_status: str = "pending",
        matched_at: datetime | None = None,
        additional_data: str | None = None,
        id: int | None = None,
    ) -> None:
        super().__init__(id)
        self.proposal_id = proposal_id
        self.extracted_politician_name = extracted_politician_name
        self.extracted_party_name = extracted_party_name
        self.extracted_parliamentary_group_name = extracted_parliamentary_group_name
        self.extracted_judgment = extracted_judgment
        self.source_url = source_url
        self.extracted_at = extracted_at or datetime.now()
        self.matched_politician_id = matched_politician_id
        self.matched_parliamentary_group_id = matched_parliamentary_group_id
        self.matching_confidence = matching_confidence
        self.matching_status = matching_status
        self.matched_at = matched_at
        self.additional_data = additional_data

    def is_matched(self) -> bool:
        """Check if the judge has been successfully matched."""
        return self.matching_status == "matched"

    def needs_review(self) -> bool:
        """Check if the judge needs manual review."""
        return self.matching_status == "needs_review"

    def convert_to_proposal_judge_params(self) -> dict[str, Any]:
        """Convert to ProposalJudge creation parameters."""
        if not self.is_matched():
            raise ValueError(
                f"Cannot convert unmatched extracted judge "
                f"(status: {self.matching_status})"
            )
        if not self.matched_politician_id:
            raise ValueError("Matched politician ID is required for conversion")

        return {
            "proposal_id": self.proposal_id,
            "politician_id": self.matched_politician_id,
            "approve": self.extracted_judgment,
        }

    def convert_to_parliamentary_group_judge_params(self) -> dict[str, Any]:
        """Convert to ProposalParliamentaryGroupJudge creation parameters."""
        if not self.is_matched():
            raise ValueError(
                f"Cannot convert unmatched extracted judge "
                f"(status: {self.matching_status})"
            )
        if not self.matched_parliamentary_group_id:
            raise ValueError(
                "Matched parliamentary group ID is required for conversion"
            )

        return {
            "proposal_id": self.proposal_id,
            "parliamentary_group_id": self.matched_parliamentary_group_id,
            "judgment": self.extracted_judgment,
        }

    def __str__(self) -> str:
        identifier = (
            self.extracted_politician_name
            or self.extracted_parliamentary_group_name
            or "Unknown"
        )
        return (
            f"ExtractedProposalJudge(name={identifier}, "
            f"judgment={self.extracted_judgment}, status={self.matching_status})"
        )
