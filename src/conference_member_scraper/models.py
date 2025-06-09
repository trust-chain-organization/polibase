"""Models for conference member scraper"""

from datetime import date
from typing import Optional

from pydantic import BaseModel, Field


class ConferenceMember(BaseModel):
    """会議体メンバー情報"""

    name: str = Field(..., description="議員名")
    role: Optional[str] = Field(None, description="役職（議長、副議長、委員長、委員など）")
    party_name: Optional[str] = Field(None, description="所属政党名")
    start_date: Optional[date] = Field(None, description="就任日")
    end_date: Optional[date] = Field(None, description="退任日（現職の場合はNone）")
    additional_info: Optional[str] = Field(None, description="その他の情報")


class ConferenceMemberList(BaseModel):
    """会議体メンバーリスト"""

    conference_id: int = Field(..., description="会議体ID")
    conference_name: str = Field(..., description="会議体名")
    url: str = Field(..., description="スクレイピング元URL")
    members: list[ConferenceMember] = Field(default_factory=list, description="メンバーリスト")
    scraped_at: date = Field(default_factory=date.today, description="スクレイピング日時")