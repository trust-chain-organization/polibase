"""Base model for all database models"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel as PydanticBaseModel
from pydantic import ConfigDict, Field


class BaseModel(PydanticBaseModel):
    """Base model with common fields and configuration"""

    model_config = ConfigDict(
        from_attributes=True,  # Enable ORM mode for SQLAlchemy compatibility
        validate_assignment=True,  # Validate on assignment
        str_strip_whitespace=True,  # Strip whitespace from strings
        use_enum_values=True,  # Use enum values instead of enum instances
    )


class TimestampedModel(BaseModel):
    """Base model with timestamp fields"""

    created_at: datetime | None = Field(None, description="作成日時")
    updated_at: datetime | None = Field(None, description="更新日時")


class DBModel(TimestampedModel):
    """Base model for database entities with ID and timestamps"""

    id: int = Field(..., description="ID")


def to_dict(model: BaseModel) -> dict[str, Any]:
    """Convert Pydantic model to dictionary for database operations"""
    data = model.model_dump(mode="python", exclude_unset=True)
    # Remove None values to avoid overwriting existing data
    return {k: v for k, v in data.items() if v is not None}
