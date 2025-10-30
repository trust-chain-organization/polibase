"""
Template for creating DTOs (Data Transfer Objects) in the Application layer.

Replace:
- OperationName: Your operation name (e.g., CreatePolitician, UpdateSpeaker)
"""

from dataclasses import dataclass, field


@dataclass
class OperationNameInputDTO:
    """
    Input DTO for [operation description].

    This DTO carries data from the interface layer to the use case.
    It should contain only data needed for the operation.
    """

    # Required fields
    name: str
    # Add your required fields

    # Optional fields
    description: str | None = None
    # Add your optional fields

    def validate(self) -> None:
        """
        Validate input data structure and basic constraints.

        Note: Complex business rules should be in domain services,
        not in DTOs. DTOs only validate structure and basic constraints.

        Raises:
            ValueError: If validation fails
        """
        # Validate required fields
        if not self.name or not self.name.strip():
            raise ValueError("Name is required")

        # Validate field constraints
        if len(self.name) > 100:
            raise ValueError("Name too long (max 100 characters)")

        # Add your validation rules here
        # Keep them simple - no complex business logic


@dataclass
class OperationNameOutputDTO:
    """
    Output DTO for [operation description].

    This DTO carries the result back to the interface layer.
    """

    # Success indicator
    success: bool

    # Result data
    entity_id: int | None = None

    # User-friendly message
    message: str = ""

    # Error details (if any)
    errors: list[str] = field(default_factory=list)

    # Additional result data
    # Add your output fields here

    def __post_init__(self) -> None:
        """Post-initialization validation."""
        if self.success and self.entity_id is None:
            raise ValueError("entity_id is required when success is True")


@dataclass
class ListOperationNameInputDTO:
    """
    Input DTO for listing entities with filters and pagination.
    """

    # Pagination
    page: int = 1
    page_size: int = 20

    # Sorting
    sort_by: str = "created_at"
    sort_order: str = "desc"  # "asc" or "desc"

    # Filters (optional)
    name_filter: str | None = None
    # Add your filter fields

    def validate(self) -> None:
        """Validate pagination and sorting parameters."""
        if self.page < 1:
            raise ValueError("page must be >= 1")
        if self.page_size < 1 or self.page_size > 100:
            raise ValueError("page_size must be between 1 and 100")
        if self.sort_order not in ["asc", "desc"]:
            raise ValueError("sort_order must be 'asc' or 'desc'")


@dataclass
class ListOperationNameOutputDTO:
    """
    Output DTO for listing entities.
    """

    success: bool
    items: list[dict] = field(default_factory=list)  # Or use specific item DTO
    total_count: int = 0
    page: int = 1
    page_size: int = 20
    message: str = ""
