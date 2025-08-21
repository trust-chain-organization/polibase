"""Base entity for domain model."""

from datetime import datetime


class BaseEntity:
    """Base class for all domain entities."""

    def __init__(self, id: int | None = None) -> None:
        self.id = id
        self.created_at: datetime | None = None
        self.updated_at: datetime | None = None

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, BaseEntity):
            return False
        return self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)
