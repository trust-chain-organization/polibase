"""議員団メンバー抽出用のモデル定義"""

from datetime import datetime

from pydantic import BaseModel, Field


class ExtractedMember(BaseModel):
    """抽出された議員団メンバー情報"""

    name: str = Field(description="議員名")
    role: str | None = Field(default=None, description="役職（団長、幹事長など）")
    party_name: str | None = Field(default=None, description="所属政党名")
    district: str | None = Field(default=None, description="選挙区")
    additional_info: str | None = Field(default=None, description="その他の情報")


class ExtractedMemberList(BaseModel):
    """抽出された議員団メンバーのリスト"""

    members: list[ExtractedMember] = Field(
        description="抽出された議員団メンバーのリスト"
    )


class MemberExtractionResult(BaseModel):
    """議員団メンバー抽出結果"""

    parliamentary_group_id: int = Field(description="議員団ID")
    url: str = Field(description="抽出元URL")
    extracted_members: list[ExtractedMember] = Field(
        description="抽出されたメンバーリスト"
    )
    extraction_date: datetime = Field(
        default_factory=datetime.now, description="抽出日時"
    )
    error: str | None = Field(default=None, description="エラーメッセージ")


class MatchingResult(BaseModel):
    """政治家マッチング結果"""

    extracted_member: ExtractedMember = Field(description="抽出されたメンバー情報")
    politician_id: int | None = Field(description="マッチした政治家ID")
    politician_name: str | None = Field(description="マッチした政治家名")
    confidence_score: float = Field(
        description="マッチング信頼度（0.0-1.0）", ge=0.0, le=1.0
    )
    matching_reason: str = Field(description="マッチング理由")


class MembershipCreationResult(BaseModel):
    """メンバーシップ作成結果"""

    total_extracted: int = Field(description="抽出されたメンバー総数")
    matched_count: int = Field(description="マッチング成功数")
    created_count: int = Field(description="作成されたメンバーシップ数")
    skipped_count: int = Field(description="スキップされた数（既存など）")
    errors: list[str] = Field(
        default_factory=list, description="エラーメッセージリスト"
    )
