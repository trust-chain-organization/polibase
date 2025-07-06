"""Parliamentary group entity."""

from src.domain.entities.base import BaseEntity


class ParliamentaryGroup(BaseEntity):
    """議員団（会派）を表すエンティティ."""

    def __init__(
        self,
        name: str,
        conference_id: int,
        url: str | None = None,
        description: str | None = None,
        is_active: bool = True,
        id: int | None = None,
    ) -> None:
        super().__init__(id)
        self.name = name
        self.conference_id = conference_id
        self.url = url
        self.description = description
        self.is_active = is_active

    def __str__(self) -> str:
        return self.name
