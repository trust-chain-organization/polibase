"""ExtractedPolitician entity module."""

from datetime import datetime

from src.domain.entities.base import BaseEntity


class ExtractedPolitician(BaseEntity):
    """LLMが抽出した政治家データの中間オブジェクトを表すエンティティ."""

    def __init__(
        self,
        name: str,
        party_id: int | None = None,
        district: str | None = None,
        profile_url: str | None = None,
        status: str = "pending",
        extracted_at: datetime | None = None,
        reviewed_at: datetime | None = None,
        reviewer_id: int | None = None,
        id: int | None = None,
    ) -> None:
        super().__init__(id)
        self.name = name
        self.party_id = party_id
        self.district = district
        self.profile_url = profile_url
        self.status = status
        self.extracted_at = extracted_at or datetime.now()
        self.reviewed_at = reviewed_at
        self.reviewer_id = reviewer_id

    def is_pending(self) -> bool:
        """Check if the politician data is pending review."""
        return self.status == "pending"

    def is_reviewed(self) -> bool:
        """Check if the politician data has been reviewed."""
        return self.status == "reviewed"

    def is_approved(self) -> bool:
        """Check if the politician data has been approved."""
        return self.status == "approved"

    def is_rejected(self) -> bool:
        """Check if the politician data has been rejected."""
        return self.status == "rejected"

    def mark_as_reviewed(self, reviewer_id: int) -> None:
        """Mark the politician data as reviewed."""
        self.status = "reviewed"
        self.reviewed_at = datetime.now()
        self.reviewer_id = reviewer_id

    def approve(self, reviewer_id: int) -> None:
        """Approve the politician data."""
        self.status = "approved"
        self.reviewed_at = datetime.now()
        self.reviewer_id = reviewer_id

    def reject(self, reviewer_id: int) -> None:
        """Reject the politician data."""
        self.status = "rejected"
        self.reviewed_at = datetime.now()
        self.reviewer_id = reviewer_id

    def __str__(self) -> str:
        return f"ExtractedPolitician(name={self.name}, status={self.status})"
