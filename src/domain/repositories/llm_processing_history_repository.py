"""LLM processing history repository interface."""

from abc import abstractmethod
from datetime import datetime

from src.domain.entities.llm_processing_history import (
    LLMProcessingHistory,
    ProcessingStatus,
    ProcessingType,
)
from src.domain.repositories.base import BaseRepository


class LLMProcessingHistoryRepository(BaseRepository[LLMProcessingHistory]):
    """Repository interface for LLM processing history."""

    @abstractmethod
    async def get_by_processing_type(
        self,
        processing_type: ProcessingType,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[LLMProcessingHistory]:
        """Get processing history by type."""
        pass

    @abstractmethod
    async def get_by_status(
        self,
        status: ProcessingStatus,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[LLMProcessingHistory]:
        """Get processing history by status."""
        pass

    @abstractmethod
    async def get_by_model(
        self,
        model_name: str,
        model_version: str | None = None,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[LLMProcessingHistory]:
        """Get processing history by model name and optionally version."""
        pass

    @abstractmethod
    async def get_by_input_reference(
        self,
        input_reference_type: str,
        input_reference_id: int,
    ) -> list[LLMProcessingHistory]:
        """Get all processing history for a specific input entity."""
        pass

    @abstractmethod
    async def get_by_date_range(
        self,
        start_date: datetime,
        end_date: datetime,
        processing_type: ProcessingType | None = None,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[LLMProcessingHistory]:
        """Get processing history within a date range."""
        pass

    @abstractmethod
    async def get_latest_by_input(
        self,
        input_reference_type: str,
        input_reference_id: int,
        processing_type: ProcessingType | None = None,
    ) -> LLMProcessingHistory | None:
        """Get the latest processing history for a specific input."""
        pass

    @abstractmethod
    async def count_by_status(
        self,
        status: ProcessingStatus,
        processing_type: ProcessingType | None = None,
    ) -> int:
        """Count processing history by status."""
        pass

    @abstractmethod
    async def search(
        self,
        processing_type: ProcessingType | None = None,
        model_name: str | None = None,
        status: ProcessingStatus | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[LLMProcessingHistory]:
        """Search processing history with multiple filters."""
        pass
