"""Conference model definitions"""

from pydantic import Field

from .base import BaseModel, DBModel


class ConferenceBase(BaseModel):
    """Base conference model with common fields"""

    name: str = Field(..., description="会議体名")
    type: str | None = Field(
        None, description="会議体タイプ（国会全体、議院、地方議会全体、常任委員会）"
    )
    governing_body_id: int = Field(..., description="開催主体ID")
    members_introduction_url: str | None = Field(None, description="議員紹介ページURL")


class ConferenceCreate(ConferenceBase):
    """Model for creating a conference"""

    pass


class ConferenceUpdate(BaseModel):
    """Model for updating a conference"""

    name: str | None = Field(None, description="会議体名")
    type: str | None = Field(
        None, description="会議体タイプ（国会全体、議院、地方議会全体、常任委員会）"
    )
    governing_body_id: int | None = Field(None, description="開催主体ID")
    members_introduction_url: str | None = Field(None, description="議員紹介ページURL")


class Conference(ConferenceBase, DBModel):
    """Complete conference model with all fields"""

    pass
