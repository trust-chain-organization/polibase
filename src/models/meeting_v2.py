"""Meeting model definitions for TypedRepository."""

from datetime import date as date_type
from datetime import datetime

from pydantic import BaseModel as PydanticBaseModel
from pydantic import Field


class MeetingBase(PydanticBaseModel):
    """Base meeting model with common fields."""

    conference_id: int = Field(..., description="会議体ID")
    date: date_type | None = Field(None, description="開催日")
    url: str | None = Field(None, description="会議関連のURLまたは議事録PDFのURL")
    name: str | None = Field(None, description="会議名")
    gcs_pdf_uri: str | None = Field(None, description="GCSに保存されたPDFのURI")
    gcs_text_uri: str | None = Field(None, description="GCSに保存されたテキストのURI")


class MeetingCreate(MeetingBase):
    """Model for creating a meeting."""

    pass


class MeetingUpdate(PydanticBaseModel):
    """Model for updating a meeting."""

    conference_id: int | None = Field(None, description="会議体ID")
    date: date_type | None = Field(None, description="開催日")
    url: str | None = Field(None, description="会議関連のURLまたは議事録PDFのURL")
    name: str | None = Field(None, description="会議名")
    gcs_pdf_uri: str | None = Field(None, description="GCSに保存されたPDFのURI")
    gcs_text_uri: str | None = Field(None, description="GCSに保存されたテキストのURI")


class Meeting(MeetingBase):
    """Complete meeting model with all fields."""

    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        """Pydantic configuration."""

        from_attributes = True
