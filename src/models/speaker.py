"""Speaker model definitions"""

from pydantic import Field

from .base import BaseModel, DBModel


class SpeakerBase(BaseModel):
    """Base speaker model with common fields"""

    name: str = Field(..., description="発言者名")
    type: str | None = Field(
        None, description="発言者タイプ（政治家、参考人、議長、政府職員）"
    )
    political_party_name: str | None = Field(
        None, description="所属政党名（政治家の場合）"
    )
    position: str | None = Field(None, description="役職・肩書き")
    is_politician: bool = Field(False, description="政治家かどうか")


class SpeakerCreate(SpeakerBase):
    """Model for creating a speaker"""

    pass


class SpeakerUpdate(BaseModel):
    """Model for updating a speaker"""

    name: str | None = Field(None, description="発言者名")
    type: str | None = Field(
        None, description="発言者タイプ（政治家、参考人、議長、政府職員）"
    )
    political_party_name: str | None = Field(
        None, description="所属政党名（政治家の場合）"
    )
    position: str | None = Field(None, description="役職・肩書き")
    is_politician: bool | None = Field(None, description="政治家かどうか")


class Speaker(SpeakerBase, DBModel):
    """Complete speaker model with all fields"""

    pass
