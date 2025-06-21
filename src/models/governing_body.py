"""Governing body model definitions"""

from pydantic import Field

from .base import BaseModel, DBModel


class GoverningBodyBase(BaseModel):
    """Base governing body model with common fields"""

    name: str = Field(..., description="開催主体名")
    type: str | None = Field(None, description="開催主体タイプ（国、都道府県、市町村）")


class GoverningBodyCreate(GoverningBodyBase):
    """Model for creating a governing body"""

    pass


class GoverningBodyUpdate(BaseModel):
    """Model for updating a governing body"""

    name: str | None = Field(None, description="開催主体名")
    type: str | None = Field(None, description="開催主体タイプ（国、都道府県、市町村）")


class GoverningBody(GoverningBodyBase, DBModel):
    """Complete governing body model with all fields"""

    pass
