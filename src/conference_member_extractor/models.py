"""Models for conference member extraction"""

from pydantic import BaseModel, Field


class ExtractedMember(BaseModel):
    """抽出された会議体メンバー情報"""

    name: str = Field(..., description="議員名")
    role: str | None = Field(None, description="役職（議長、副議長、委員長、委員など）")
    party_name: str | None = Field(None, description="所属政党名")
    additional_info: str | None = Field(None, description="その他の情報")
