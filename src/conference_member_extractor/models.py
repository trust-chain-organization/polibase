"""Models for conference member extraction"""

from datetime import date
from typing import Optional

from pydantic import BaseModel, Field


class ExtractedMember(BaseModel):
    """抽出された会議体メンバー情報"""

    name: str = Field(..., description="議員名")
    role: Optional[str] = Field(None, description="役職（議長、副議長、委員長、委員など）")
    party_name: Optional[str] = Field(None, description="所属政党名")
    additional_info: Optional[str] = Field(None, description="その他の情報")