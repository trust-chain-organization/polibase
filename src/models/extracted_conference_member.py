"""ExtractedConferenceMember model."""

from datetime import datetime

from pydantic import BaseModel as PydanticBaseModel
from pydantic import ConfigDict, Field

from src.models.base import DBModel


class ExtractedConferenceMemberBase(PydanticBaseModel):
    """Base extracted conference member model with common fields."""

    conference_id: int = Field(..., description="会議体ID")
    extracted_name: str = Field(..., description="抽出された名前")
    source_url: str = Field(..., description="ソースURL")
    extracted_role: str | None = Field(None, description="抽出された役職")
    extracted_party_name: str | None = Field(None, description="抽出された政党名")
    extracted_at: datetime = Field(default_factory=datetime.now, description="抽出日時")
    matched_politician_id: int | None = Field(None, description="マッチした政治家ID")
    matching_confidence: float | None = Field(None, description="マッチング信頼度")
    matching_status: str = Field("pending", description="マッチングステータス")
    matched_at: datetime | None = Field(None, description="マッチング日時")
    additional_data: str | None = Field(None, description="追加データ")


class ExtractedConferenceMemberCreate(ExtractedConferenceMemberBase):
    """Model for creating a new extracted conference member."""

    pass


class ExtractedConferenceMemberUpdate(PydanticBaseModel):
    """Model for updating an existing extracted conference member."""

    matched_politician_id: int | None = Field(None, description="マッチした政治家ID")
    matching_confidence: float | None = Field(None, description="マッチング信頼度")
    matching_status: str | None = Field(None, description="マッチングステータス")
    matched_at: datetime | None = Field(None, description="マッチング日時")


class ExtractedConferenceMember(ExtractedConferenceMemberBase, DBModel):
    """Complete extracted conference member model with all fields."""

    model_config = ConfigDict(from_attributes=True)
