"""Models for party member extraction"""

from pydantic import BaseModel, Field


class PartyMemberInfo(BaseModel):
    """政党所属議員の情報"""

    name: str = Field(description="議員の氏名（姓名）")
    position: str | None = Field(
        description="役職（衆議院議員、参議院議員など）", default=None
    )
    electoral_district: str | None = Field(
        description="選挙区（例：東京1区、比例北海道）", default=None
    )
    prefecture: str | None = Field(
        description="都道府県（例：東京都、北海道）", default=None
    )
    profile_url: str | None = Field(description="プロフィールページのURL", default=None)
    party_position: str | None = Field(
        description="党内役職（代表、幹事長など）", default=None
    )


class PartyMemberList(BaseModel):
    """政党所属議員のリスト"""

    members: list[PartyMemberInfo] = Field(
        description="抽出された議員のリスト",
        default_factory=lambda: [],  # pyrightの型推論エラー対策
    )
    total_count: int = Field(description="抽出された議員の総数", default=0)
    party_name: str | None = Field(description="政党名", default=None)

    def __len__(self):
        return len(self.members)


class WebPageContent(BaseModel):
    """Webページのコンテンツ"""

    url: str = Field(description="ページのURL")
    html_content: str = Field(description="HTMLコンテンツ")
    page_number: int | None = Field(
        description="ページ番号（ページネーションがある場合）", default=None
    )
