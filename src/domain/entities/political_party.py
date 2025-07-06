"""Political party entity."""

from src.domain.entities.base import BaseEntity


class PoliticalParty(BaseEntity):
    """政党を表すエンティティ."""

    def __init__(
        self,
        name: str,
        members_list_url: str | None = None,
        id: int | None = None,
    ) -> None:
        super().__init__(id)
        self.name = name
        self.members_list_url = members_list_url

    def __str__(self) -> str:
        return self.name
