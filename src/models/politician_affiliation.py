"""PoliticianAffiliation model."""

from datetime import date

from pydantic import BaseModel as PydanticBaseModel
from pydantic import ConfigDict, Field

from src.models.base import DBModel


class PoliticianAffiliationBase(PydanticBaseModel):
    """Base politician affiliation model with common fields."""

    politician_id: int = Field(..., description="政治家ID")
    conference_id: int = Field(..., description="会議体ID")
    start_date: date = Field(..., description="所属開始日")
    end_date: date | None = Field(None, description="所属終了日")
    role: str | None = Field(None, description="役職")


class PoliticianAffiliationCreate(PoliticianAffiliationBase):
    """Model for creating a new politician affiliation."""

    pass


class PoliticianAffiliationUpdate(PydanticBaseModel):
    """Model for updating an existing politician affiliation."""

    end_date: date | None = Field(None, description="所属終了日")
    role: str | None = Field(None, description="役職")


class PoliticianAffiliation(PoliticianAffiliationBase, DBModel):
    """Complete politician affiliation model with all fields."""

    model_config = ConfigDict(from_attributes=True)
