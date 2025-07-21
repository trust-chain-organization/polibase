"""Instrumented LLM Service with automatic history recording."""

import logging
from collections.abc import Awaitable, Callable
from typing import Any

from src.domain.entities.llm_processing_history import (
    LLMProcessingHistory,
    ProcessingStatus,
    ProcessingType,
)
from src.domain.repositories.llm_processing_history_repository import (
    LLMProcessingHistoryRepository,
)
from src.domain.repositories.prompt_version_repository import PromptVersionRepository
from src.domain.types import (
    LLMExtractResult,
    LLMMatchResult,
    LLMSpeakerMatchContext,
    PoliticianDTO,
)
from src.infrastructure.interfaces.llm_service import ILLMService

logger = logging.getLogger(__name__)


class InstrumentedLLMService:
    """Decorator for LLM services that adds automatic history recording."""

    def __init__(
        self,
        llm_service: ILLMService,
        history_repository: LLMProcessingHistoryRepository | None = None,
        prompt_repository: PromptVersionRepository | None = None,
        model_name: str = "unknown",
        model_version: str = "unknown",
        input_reference_type: str | None = None,
        input_reference_id: int | None = None,
    ):
        """Initialize instrumented LLM service.

        Args:
            llm_service: The underlying LLM service to wrap
            history_repository: Repository for storing processing history
            prompt_repository: Repository for prompt version management
            model_name: Name of the LLM model
            model_version: Version of the LLM model
        """
        self._llm_service = llm_service
        self._history_repository = history_repository
        self._prompt_repository = prompt_repository
        self._model_name = model_name
        self._model_version = model_version
        self._input_reference_type = input_reference_type
        self._input_reference_id = input_reference_id

    @property
    def temperature(self) -> float:
        """Get the temperature from the underlying LLM service."""
        return self._llm_service.temperature

    def set_input_reference(
        self, reference_type: str | None, reference_id: int | None
    ) -> None:
        """Set the input reference for history tracking.

        Args:
            reference_type: Type of reference (e.g., 'meeting')
            reference_id: ID of the reference
        """
        self._input_reference_type = reference_type
        self._input_reference_id = reference_id

    async def set_history_repository(
        self, repository: LLMProcessingHistoryRepository | None
    ) -> None:
        """Set the history repository for recording LLM operations."""
        self._history_repository = repository

    async def get_processing_history(
        self, reference_type: str | None = None, reference_id: int | None = None
    ) -> list[LLMProcessingHistory]:
        """Get processing history for this service."""
        if not self._history_repository:
            return []

        if reference_type and reference_id:
            return await self._history_repository.get_by_input_reference(
                reference_type, reference_id
            )
        return []

    async def _record_processing(
        self,
        processing_type: ProcessingType,
        input_reference_type: str,
        input_reference_id: int,
        prompt_template: str,
        prompt_variables: dict[str, Any],
        processing_func: Callable[..., Awaitable[Any]],
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        """Record LLM processing with history tracking.

        Args:
            processing_type: Type of processing
            input_reference_type: Type of entity being processed
            input_reference_id: ID of entity being processed
            prompt_template: Template used for the prompt
            prompt_variables: Variables used in the prompt
            processing_func: The actual processing function to call
            *args: Arguments for the processing function
            **kwargs: Keyword arguments for the processing function

        Returns:
            Result from the processing function
        """
        # Create history entry
        history_entry = None
        if self._history_repository:
            history_entry = LLMProcessingHistory(
                processing_type=processing_type,
                model_name=self._model_name,
                model_version=self._model_version,
                prompt_template=prompt_template,
                prompt_variables=prompt_variables,
                input_reference_type=input_reference_type,
                input_reference_id=input_reference_id,
                status=ProcessingStatus.PENDING,
                processing_metadata={
                    "args_count": len(args),
                    "kwargs_keys": list(kwargs.keys()),
                },
            )
            history_entry.start_processing()

            try:
                # Save initial entry
                history_entry = await self._history_repository.create(history_entry)
            except Exception as e:
                logger.error(f"Failed to create history entry: {e}")
                history_entry = None

        try:
            # Execute the actual processing
            result = await processing_func(*args, **kwargs)

            # Update history with success
            if history_entry and self._history_repository:
                # Extract result metadata
                result_metadata = self._extract_result_metadata(result)
                history_entry.complete_processing(result_metadata)
                await self._history_repository.update(history_entry)

            return result

        except Exception as e:
            # Update history with failure
            if history_entry and self._history_repository:
                history_entry.fail_processing(str(e))
                await self._history_repository.update(history_entry)

            # Re-raise the exception
            raise

    def _extract_result_metadata(self, result: Any) -> dict[str, Any]:
        """Extract metadata from processing result.

        Args:
            result: The processing result

        Returns:
            Dictionary of metadata
        """
        metadata: dict[str, Any] = {"type": type(result).__name__}

        if isinstance(result, dict):
            # For dict results, include some key info
            metadata["keys"] = list(result.keys()) if result else []  # type: ignore[arg-type]
            if "matched" in result:
                metadata["matched"] = result["matched"]
            if "confidence" in result:
                metadata["confidence"] = result["confidence"]
            if "success" in result:
                metadata["success"] = result["success"]
        elif isinstance(result, list):
            metadata["count"] = len(result)  # type: ignore[arg-type]
        elif result is None:
            metadata["is_null"] = True

        return metadata

    async def match_speaker_to_politician(
        self, context: LLMSpeakerMatchContext
    ) -> LLMMatchResult | None:
        """Match a speaker to a politician using LLM with history recording."""
        # Extract prompt information
        prompt_template = "speaker_matching"  # This would be from prompt manager
        prompt_variables: dict[str, Any] = {
            "speaker_name": context.get("speaker_name", ""),
            "candidates_count": len(context.get("candidates", [])),
        }

        # Get reference info from context
        reference_type = "speaker"
        reference_id = context.get("speaker_id", 0)

        return await self._record_processing(
            ProcessingType.SPEAKER_MATCHING,
            reference_type,
            reference_id,
            prompt_template,
            prompt_variables,
            self._llm_service.match_speaker_to_politician,
            context,
        )

    async def extract_speeches_from_text(self, text: str) -> list[dict[str, str]]:
        """Extract speeches from meeting minutes text with history recording."""
        prompt_template = "speech_extraction"
        prompt_variables = {"text_length": len(text)}

        # Use configured reference type/id if available, otherwise use defaults
        reference_type = self._input_reference_type or "text"
        reference_id = (
            self._input_reference_id
            if self._input_reference_id is not None
            else hash(text[:100]) % 1000000  # Simple hash for tracking
        )

        return await self._record_processing(
            ProcessingType.SPEECH_EXTRACTION,
            reference_type,
            reference_id,
            prompt_template,
            prompt_variables,
            self._llm_service.extract_speeches_from_text,
            text,
        )

    async def process_minutes_division(
        self,
        processing_func: Callable[..., Awaitable[Any]],
        prompt_name: str,
        prompt_variables: dict[str, Any],
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        """Process minutes division operations with history recording."""
        # Use configured reference type/id if available
        reference_type = self._input_reference_type or "meeting"
        reference_id = self._input_reference_id or 0

        return await self._record_processing(
            ProcessingType.MINUTES_DIVISION,
            reference_type,
            reference_id,
            prompt_name,
            prompt_variables,
            processing_func,
            *args,
            **kwargs,
        )

    async def extract_party_members(
        self, html_content: str, party_id: int
    ) -> LLMExtractResult:
        """Extract party member information from HTML with history recording."""
        prompt_template = "party_member_extraction"
        prompt_variables = {"html_length": len(html_content), "party_id": party_id}

        reference_type = "party"
        reference_id = party_id

        return await self._record_processing(
            ProcessingType.POLITICIAN_EXTRACTION,
            reference_type,
            reference_id,
            prompt_template,
            prompt_variables,
            self._llm_service.extract_party_members,
            html_content,
            party_id,
        )

    async def match_conference_member(
        self, member_name: str, party_name: str | None, candidates: list[PoliticianDTO]
    ) -> LLMMatchResult | None:
        """Match a conference member to a politician with history recording."""
        prompt_template = "conference_member_matching"
        prompt_variables: dict[str, Any] = {
            "member_name": member_name,
            "party_name": party_name,
            "candidates_count": len(candidates),
        }

        # Use a hash of member name for reference
        reference_type = "conference_member"
        reference_id = hash(member_name) % 1000000

        return await self._record_processing(
            ProcessingType.CONFERENCE_MEMBER_MATCHING,
            reference_type,
            reference_id,
            prompt_template,
            prompt_variables,
            self._llm_service.match_conference_member,
            member_name,
            party_name,
            candidates,
        )

    # Delegation methods for ILLMService compatibility
    def get_structured_llm(self, schema: Any) -> Any:
        """Delegate to wrapped LLM service."""
        return self._llm_service.get_structured_llm(schema)

    def get_prompt(self, prompt_name: str) -> Any:
        """Delegate to wrapped LLM service."""
        return self._llm_service.get_prompt(prompt_name)

    def invoke_with_retry(self, chain: Any, inputs: dict[str, Any]) -> Any:
        """Delegate to wrapped LLM service."""
        return self._llm_service.invoke_with_retry(chain, inputs)

    # Attribute delegation for compatibility
    @property
    def model_name(self) -> str:
        """Get model name from wrapped service or return configured name."""
        if hasattr(self._llm_service, "model_name"):
            return self._llm_service.model_name
        return self._model_name


    def __getattr__(self, name: str) -> Any:
        """Delegate unknown attributes to wrapped service."""
        return getattr(self._llm_service, name)
