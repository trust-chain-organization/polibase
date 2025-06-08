from pydantic import BaseModel, Field


class PoliticianInfo(BaseModel):
    name: str = Field(..., description="政治家の名前")
    party: str | None = Field(None, description="所属政党")
    position: str | None = Field(None, description="役職")


class PoliticianInfoList(BaseModel):
    politician_info_list: list[PoliticianInfo] = Field(
        default_factory=list, description="政治家情報のリスト"
    )


class PoliticianProcessState(BaseModel):
    original_minutes: str = Field(..., description="元の議事録全体")
    politician_info_list: list[PoliticianInfo] = Field(
        default_factory=list, description="抽出された政治家情報のリスト"
    )
