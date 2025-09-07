"""Proposal entity module."""

from src.domain.entities.base import BaseEntity


class Proposal(BaseEntity):
    """議案を表すエンティティ."""

    def __init__(
        self,
        content: str,
        status: str | None = None,
        id: int | None = None,
    ) -> None:
        super().__init__(id)
        self.content = content
        self.status = status

    def __str__(self) -> str:
        return f"Proposal {self.id}: {self.content[:50]}..."
