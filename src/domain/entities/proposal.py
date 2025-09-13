"""Proposal entity module."""

from src.domain.entities.base import BaseEntity


class Proposal(BaseEntity):
    """議案を表すエンティティ."""

    def __init__(
        self,
        content: str,
        status: str | None = None,
        detail_url: str | None = None,
        status_url: str | None = None,
        submission_date: str | None = None,  # ISO形式の日付文字列
        submitter: str | None = None,
        proposal_number: str | None = None,
        meeting_id: int | None = None,
        summary: str | None = None,
        id: int | None = None,
    ) -> None:
        super().__init__(id)
        self.content = content
        self.status = status
        self.detail_url = detail_url
        self.status_url = status_url
        self.submission_date = submission_date
        self.submitter = submitter
        self.proposal_number = proposal_number
        self.meeting_id = meeting_id
        self.summary = summary

    def __str__(self) -> str:
        identifier = self.proposal_number or f"ID:{self.id}"
        return f"Proposal {identifier}: {self.content[:50]}..."
