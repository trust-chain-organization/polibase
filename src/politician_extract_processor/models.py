from pydantic import BaseModel, Field
from typing import List, Optional

class PoliticianInfo(BaseModel):
    name: str = Field(..., description="政治家の名前")
    party: Optional[str] = Field(None, description="所属政党")
    position: Optional[str] = Field(None, description="役職")

class PoliticianInfoList(BaseModel):
    politician_info_list: List[PoliticianInfo] = Field(default_factory=list, description="政治家情報のリスト")

class PoliticianProcessState(BaseModel):
    original_minutes: str = Field(..., description="元の議事録全体")
    politician_info_list: List[PoliticianInfo] = Field(default_factory=list, description="抽出された政治家情報のリスト")
    current_section: str = Field(default="", description="現在処理中のセクション")
    section_index: int = Field(default=0, description="現在処理中のセクションのインデックス") 