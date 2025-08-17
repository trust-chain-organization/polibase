"""ExtractedConferenceMember entity."""

from datetime import datetime

from src.domain.entities.base import BaseEntity


class ExtractedConferenceMember(BaseEntity):
    """会議体メンバー抽出情報を表すエンティティ."""

    def __init__(
        self,
        conference_id: int,
        extracted_name: str,
        source_url: str,
        extracted_role: str | None = None,
        extracted_party_name: str | None = None,
        extracted_at: datetime | None = None,
        matched_politician_id: int | None = None,
        matching_confidence: float | None = None,
        matching_status: str = "pending",
        matched_at: datetime | None = None,
        additional_data: str | None = None,
        id: int | None = None,
    ) -> None:
        super().__init__(id)
        self.conference_id = conference_id
        self.extracted_name = extracted_name
        self.source_url = source_url
        self.extracted_role = extracted_role
        self.extracted_party_name = extracted_party_name
        self.extracted_at = extracted_at or datetime.now()
        self.matched_politician_id = matched_politician_id
        self.matching_confidence = matching_confidence
        self.matching_status = matching_status
        self.matched_at = matched_at
        self.additional_data = additional_data

    def is_matched(self) -> bool:
        """Check if the member has been successfully matched."""
        return self.matching_status == "matched"

    def needs_review(self) -> bool:
        """Check if the member needs manual review."""
        return self.matching_status == "needs_review"

    def __str__(self) -> str:
        return (
            f"ExtractedConferenceMember(name={self.extracted_name}, "
            f"status={self.matching_status})"
        )
