"""Politician model definitions"""

from pydantic import Field

from .base import BaseModel, DBModel


class PoliticianBase(BaseModel):
    """Base politician model with common fields"""

    name: str = Field(..., description="政治家名")
    political_party_id: int | None = Field(None, description="現在の主要所属政党ID")
    prefecture: str | None = Field(None, description="都道府県", max_length=10)
    electoral_district: str | None = Field(None, description="選挙区")
    profile_url: str | None = Field(None, description="プロフィールページURL")
    party_position: str | None = Field(None, description="党内役職（代表、幹事長など）")


class PoliticianCreate(PoliticianBase):
    """Model for creating a politician"""

    pass


class PoliticianUpdate(BaseModel):
    """Model for updating a politician"""

    name: str | None = Field(None, description="政治家名")
    political_party_id: int | None = Field(None, description="現在の主要所属政党ID")
    prefecture: str | None = Field(None, description="都道府県", max_length=10)
    electoral_district: str | None = Field(None, description="選挙区")
    profile_url: str | None = Field(None, description="プロフィールページURL")
    party_position: str | None = Field(None, description="党内役職（代表、幹事長など）")


class Politician(PoliticianBase, DBModel):
    """Complete politician model with all fields

    Note: Speaker-Politician relationship is now managed through
    speakers.politician_id (many-to-one), not politicians.speaker_id.
    See Issue #531 for details.
    """

    pass
