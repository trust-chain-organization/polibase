"""
Template for creating a new domain entity.

Replace:
- EntityName: Your entity name (e.g., Politician, Speaker)
- field_name: Your field names
- FieldType: Your field types
"""

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class EntityName:
    """
    Domain entity representing [description].

    Business Rules:
    - [List key business rules here]
    - [e.g., name cannot be empty]
    - [e.g., email must be unique]
    """

    # Primary key (None for new entities)
    id: int | None

    # Required fields
    name: str
    # Add your required fields here

    # Optional fields
    description: str | None = None
    # Add your optional fields here

    # Timestamps (usually managed by repository)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self) -> None:
        """Validate entity state after initialization."""
        self.validate()

    def validate(self) -> None:
        """
        Validate business rules.

        Raises:
            ValueError: If validation fails
        """
        if not self.name or not self.name.strip():
            raise ValueError("Name is required")

        # Add your validation rules here
        # Example:
        # if len(self.name) > 100:
        #     raise ValueError("Name too long (max 100 characters)")

    def update_name(self, new_name: str) -> None:
        """
        Update entity name with business rule validation.

        Args:
            new_name: New name value

        Raises:
            ValueError: If new name is invalid
        """
        if not new_name or not new_name.strip():
            raise ValueError("Name cannot be empty")

        self.name = new_name
        self.updated_at = datetime.now()

    # Add other business methods here
    # Keep them focused on this entity's state and rules
