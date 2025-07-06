"""Governing body entity."""

from src.domain.entities.base import BaseEntity


class GoverningBody(BaseEntity):
    """開催主体（国、都道府県、市町村）を表すエンティティ."""

    def __init__(
        self,
        name: str,
        type: str | None = None,
        organization_code: str | None = None,
        organization_type: str | None = None,
        id: int | None = None,
    ) -> None:
        super().__init__(id)
        self.name = name
        self.type = type
        self.organization_code = organization_code
        self.organization_type = organization_type

    def __str__(self) -> str:
        return f"{self.name} ({self.type})" if self.type else self.name
