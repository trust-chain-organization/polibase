"""Parliamentary group model definitions"""

import datetime

from pydantic import Field

from .base import BaseModel, DBModel


class ParliamentaryGroupBase(BaseModel):
    """Base parliamentary group model with common fields"""

    name: str = Field(..., description="議員団名")
    conference_id: int = Field(..., description="所属する会議体ID")
    description: str | None = Field(None, description="議員団の説明")
    is_active: bool = Field(True, description="現在活動中かどうか")


class ParliamentaryGroupCreate(ParliamentaryGroupBase):
    """Model for creating a parliamentary group"""

    pass


class ParliamentaryGroupUpdate(BaseModel):
    """Model for updating a parliamentary group"""

    name: str | None = Field(None, description="議員団名")
    conference_id: int | None = Field(None, description="所属する会議体ID")
    description: str | None = Field(None, description="議員団の説明")
    is_active: bool | None = Field(None, description="現在活動中かどうか")


class ParliamentaryGroup(ParliamentaryGroupBase, DBModel):
    """Complete parliamentary group model with all fields"""

    pass


class ParliamentaryGroupMembershipBase(BaseModel):
    """Base parliamentary group membership model with common fields"""

    parliamentary_group_id: int = Field(..., description="議員団ID")
    politician_id: int = Field(..., description="政治家ID")
    role: str | None = Field(None, description="役職（団長、幹事長、会計など）")
    start_date: datetime.date = Field(..., description="所属開始日")
    end_date: datetime.date | None = Field(
        None, description="所属終了日（現在も所属している場合はNULL）"
    )


class ParliamentaryGroupMembershipCreate(ParliamentaryGroupMembershipBase):
    """Model for creating a parliamentary group membership"""

    pass


class ParliamentaryGroupMembership(ParliamentaryGroupMembershipBase, DBModel):
    """Complete parliamentary group membership model with all fields"""

    pass
