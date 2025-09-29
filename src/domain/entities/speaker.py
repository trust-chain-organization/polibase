"""Speaker entity."""

from src.domain.entities.base import BaseEntity


class Speaker(BaseEntity):
    """発言者を表すエンティティ."""

    def __init__(
        self,
        name: str,
        type: str | None = None,
        political_party_name: str | None = None,
        position: str | None = None,
        is_politician: bool = False,
        politician_id: int | None = None,
        id: int | None = None,
    ) -> None:
        super().__init__(id)
        self.name = name
        self.type = type
        self.political_party_name = political_party_name
        self.position = position
        self.is_politician = is_politician
        self.politician_id = politician_id

    def __str__(self) -> str:
        parts = [self.name]
        if self.position:
            parts.append(f"({self.position})")
        if self.political_party_name:
            parts.append(f"- {self.political_party_name}")
        return " ".join(parts)
