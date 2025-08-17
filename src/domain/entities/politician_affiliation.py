"""PoliticianAffiliation entity."""

from datetime import date

from src.domain.entities.base import BaseEntity


class PoliticianAffiliation(BaseEntity):
    """政治家の所属を表すエンティティ."""

    def __init__(
        self,
        politician_id: int,
        conference_id: int,
        start_date: date,
        end_date: date | None = None,
        role: str | None = None,
        id: int | None = None,
    ) -> None:
        super().__init__(id)
        self.politician_id = politician_id
        self.conference_id = conference_id
        self.start_date = start_date
        self.end_date = end_date
        self.role = role

    def is_active(self) -> bool:
        """Check if the affiliation is currently active."""
        return self.end_date is None

    def __str__(self) -> str:
        status = "active" if self.is_active() else f"ended {self.end_date}"
        return (
            f"PoliticianAffiliation(politician={self.politician_id}, "
            f"conference={self.conference_id}, {status})"
        )
