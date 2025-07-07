"""Governing body model definitions."""

from datetime import datetime

from pydantic import BaseModel as PydanticBaseModel
from pydantic import Field


class GoverningBodyBase(PydanticBaseModel):
    """Base governing body model with common fields."""

    name: str = Field(..., description="組織名")
    type: str | None = Field(None, description="組織タイプ（国、都道府県、市町村）")


class GoverningBodyCreate(GoverningBodyBase):
    """Model for creating a governing body."""

    pass


class GoverningBodyUpdate(PydanticBaseModel):
    """Model for updating a governing body."""

    name: str | None = Field(None, description="組織名")
    type: str | None = Field(None, description="組織タイプ（国、都道府県、市町村）")


class GoverningBody(GoverningBodyBase):
    """Complete governing body model with all fields."""

    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        """Pydantic configuration."""

        from_attributes = True
