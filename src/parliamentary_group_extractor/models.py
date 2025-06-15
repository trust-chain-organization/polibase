"""議員団メンバー抽出のためのデータモデル"""

from datetime import date

from pydantic import BaseModel, Field


class ParliamentaryGroupMember(BaseModel):
    """議員団メンバー情報"""

    name: str = Field(description="議員の氏名（敬称なし）")
    role: str | None = Field(
        None, description="議員団内での役職（団長、幹事長、政調会長など）"
    )
    political_party: str | None = Field(None, description="所属政党名")
    electoral_district: str | None = Field(None, description="選挙区・地域")
    profile_url: str | None = Field(None, description="プロフィールページのURL")
    additional_info: str | None = Field(None, description="その他の情報")


class ParliamentaryGroupMemberList(BaseModel):
    """議員団メンバーリスト"""

    members: list[ParliamentaryGroupMember] = Field(
        default_factory=list, description="議員団メンバーのリスト"
    )
    parliamentary_group_name: str = Field(description="議員団名")
    total_count: int = Field(description="メンバー総数")
    extraction_date: date | None = Field(None, description="抽出日（デフォルトは今日）")
    source_url: str = Field(description="抽出元のURL")
