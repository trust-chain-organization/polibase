"""Politician model definitions"""

from pydantic import Field

from .base import BaseModel, DBModel


class PoliticianBase(BaseModel):
    """Base politician model with common fields"""

    name: str = Field(..., description="政治家名")
    political_party_id: int | None = Field(None, description="現在の主要所属政党ID")
    position: str | None = Field(None, description="役職（衆議院議員、参議院議員など）")
    prefecture: str | None = Field(None, description="都道府県", max_length=10)
    electoral_district: str | None = Field(None, description="選挙区")
    profile_url: str | None = Field(None, description="プロフィールページURL")
    party_position: str | None = Field(None, description="党内役職（代表、幹事長など）")


class PoliticianCreate(PoliticianBase):
    """Model for creating a politician"""

    speaker_id: int | None = Field(None, description="関連する発言者ID")


class PoliticianUpdate(BaseModel):
    """Model for updating a politician"""

    name: str | None = Field(None, description="政治家名")
    political_party_id: int | None = Field(None, description="現在の主要所属政党ID")
    position: str | None = Field(None, description="役職（衆議院議員、参議院議員など）")
    prefecture: str | None = Field(None, description="都道府県", max_length=10)
    electoral_district: str | None = Field(None, description="選挙区")
    profile_url: str | None = Field(None, description="プロフィールページURL")
    party_position: str | None = Field(None, description="党内役職（代表、幹事長など）")
    speaker_id: int | None = Field(None, description="関連する発言者ID")


class Politician(PoliticianBase, DBModel):
    """Complete politician model with all fields"""

    speaker_id: int | None = Field(None, description="関連する発言者ID")
