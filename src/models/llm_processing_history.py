"""LLM processing history model definitions."""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel as PydanticBaseModel
from pydantic import ConfigDict, Field


class ProcessingType(str, Enum):
    """Types of LLM processing."""

    MINUTES_DIVISION = "minutes_division"
    SPEECH_EXTRACTION = "speech_extraction"
    SPEAKER_MATCHING = "speaker_matching"
    POLITICIAN_EXTRACTION = "politician_extraction"
    CONFERENCE_MEMBER_MATCHING = "conference_member_matching"
    PARLIAMENTARY_GROUP_EXTRACTION = "parliamentary_group_extraction"


class ProcessingStatus(str, Enum):
    """Status of LLM processing."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class LLMProcessingHistoryBase(PydanticBaseModel):
    """Base LLM processing history model with common fields."""

    processing_type: ProcessingType = Field(..., description="処理タイプ")
    model_name: str = Field(..., description="使用したLLMモデル名")
    model_version: str = Field(..., description="モデルバージョン")
    prompt_template: str = Field(..., description="プロンプトテンプレート")
    prompt_variables: dict[str, Any] = Field(
        default_factory=dict, description="プロンプト変数"
    )
    input_reference_type: str = Field(..., description="処理対象エンティティタイプ")
    input_reference_id: int = Field(..., description="処理対象エンティティID")
    status: ProcessingStatus = Field(
        ProcessingStatus.PENDING, description="処理ステータス"
    )
    result: dict[str, Any] | None = Field(None, description="処理結果")
    error_message: str | None = Field(None, description="エラーメッセージ")
    processing_metadata: dict[str, Any] = Field(
        default_factory=dict, description="追加メタデータ"
    )
    started_at: datetime | None = Field(None, description="処理開始時刻")
    completed_at: datetime | None = Field(None, description="処理完了時刻")


class LLMProcessingHistoryCreate(LLMProcessingHistoryBase):
    """Model for creating LLM processing history."""

    pass


class LLMProcessingHistoryUpdate(PydanticBaseModel):
    """Model for updating LLM processing history."""

    status: ProcessingStatus | None = Field(None, description="処理ステータス")
    result: dict[str, Any] | None = Field(None, description="処理結果")
    error_message: str | None = Field(None, description="エラーメッセージ")
    processing_metadata: dict[str, Any] | None = Field(
        None, description="追加メタデータ"
    )
    started_at: datetime | None = Field(None, description="処理開始時刻")
    completed_at: datetime | None = Field(None, description="処理完了時刻")


class LLMProcessingHistory(LLMProcessingHistoryBase):
    """Complete LLM processing history model with all fields."""

    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @property
    def processing_duration_seconds(self) -> float | None:
        """Calculate processing duration in seconds."""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None
