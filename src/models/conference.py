"""Conference model definitions."""

from datetime import datetime

from pydantic import BaseModel as PydanticBaseModel
from pydantic import ConfigDict, Field


class ConferenceBase(PydanticBaseModel):
    """Base conference model with common fields."""

    name: str = Field(..., description="会議体名")
    type: str | None = Field(None, description="会議体タイプ")
    governing_body_id: int = Field(..., description="開催主体ID")


class ConferenceCreate(ConferenceBase):
    """Model for creating a conference."""

    pass


class ConferenceUpdate(PydanticBaseModel):
    """Model for updating a conference."""

    name: str | None = Field(None, description="会議体名")
    type: str | None = Field(None, description="会議体タイプ")
    governing_body_id: int | None = Field(None, description="開催主体ID")


class Conference(ConferenceBase):
    """Complete conference model with all fields."""

    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
