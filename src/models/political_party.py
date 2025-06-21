"""Political party model definitions"""

from pydantic import Field

from .base import BaseModel, DBModel


class PoliticalPartyBase(BaseModel):
    """Base political party model with common fields"""

    name: str = Field(..., description="政党名")
    members_list_url: str | None = Field(None, description="党員リストURL")


class PoliticalPartyCreate(PoliticalPartyBase):
    """Model for creating a political party"""

    pass


class PoliticalPartyUpdate(BaseModel):
    """Model for updating a political party"""

    name: str | None = Field(None, description="政党名")
    members_list_url: str | None = Field(None, description="党員リストURL")


class PoliticalParty(PoliticalPartyBase, DBModel):
    """Complete political party model with all fields"""

    pass
