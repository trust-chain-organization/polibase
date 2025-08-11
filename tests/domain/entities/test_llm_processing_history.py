"""Tests for LLM processing history entity."""

from datetime import datetime

from src.domain.entities.llm_processing_history import (
    LLMProcessingHistory,
    ProcessingStatus,
    ProcessingType,
)


class TestLLMProcessingHistory:
    """Test cases for LLMProcessingHistory entity."""

    def test_create_entity(self):
        """Test creating an LLM processing history entity."""
        entity = LLMProcessingHistory(
            processing_type=ProcessingType.MINUTES_DIVISION,
            model_name="gemini-2.0-flash",
            model_version="2.0.0",
            prompt_template="Divide the minutes into sections",
            prompt_variables={"minutes": "test content"},
            input_reference_type="meeting",
            input_reference_id=123,
            status=ProcessingStatus.PENDING,
            processing_metadata={"temperature": 0.7},
            created_by="test_user",
        )

        assert entity.processing_type == ProcessingType.MINUTES_DIVISION
        assert entity.model_name == "gemini-2.0-flash"
        assert entity.model_version == "2.0.0"
        assert entity.prompt_template == "Divide the minutes into sections"
        assert entity.prompt_variables == {"minutes": "test content"}
        assert entity.input_reference_type == "meeting"
        assert entity.input_reference_id == 123
        assert entity.status == ProcessingStatus.PENDING
        assert entity.processing_metadata == {"temperature": 0.7}
        assert entity.result is None
        assert entity.error_message is None
        assert entity.started_at is None
        assert entity.completed_at is None
        assert entity.created_by == "test_user"

    def test_start_processing(self):
        """Test starting processing updates status and timestamp."""
        entity = LLMProcessingHistory(
            processing_type=ProcessingType.SPEAKER_MATCHING,
            model_name="gemini-2.0-flash",
            model_version="2.0.0",
            prompt_template="Match speaker",
            prompt_variables={},
            input_reference_type="speaker",
            input_reference_id=456,
        )

        entity.start_processing()

        assert entity.status == ProcessingStatus.IN_PROGRESS
        assert entity.started_at is not None
        assert isinstance(entity.started_at, datetime)

    def test_complete_processing(self):
        """Test completing processing updates status, result, and timestamp."""
        entity = LLMProcessingHistory(
            processing_type=ProcessingType.POLITICIAN_EXTRACTION,
            model_name="gemini-2.0-flash",
            model_version="2.0.0",
            prompt_template="Extract politicians",
            prompt_variables={},
            input_reference_type="party",
            input_reference_id=789,
        )

        entity.start_processing()
        result = {"politicians": [{"name": "Test Politician"}]}
        entity.complete_processing(result)

        assert entity.status == ProcessingStatus.COMPLETED
        assert entity.result == result
        assert entity.completed_at is not None
        assert isinstance(entity.completed_at, datetime)

    def test_fail_processing(self):
        """Test failing processing updates status, error, and timestamp."""
        entity = LLMProcessingHistory(
            processing_type=ProcessingType.CONFERENCE_MEMBER_MATCHING,
            model_name="gemini-2.0-flash",
            model_version="2.0.0",
            prompt_template="Match member",
            prompt_variables={},
            input_reference_type="conference",
            input_reference_id=101,
        )

        entity.start_processing()
        error_message = "API rate limit exceeded"
        entity.fail_processing(error_message)

        assert entity.status == ProcessingStatus.FAILED
        assert entity.error_message == error_message
        assert entity.completed_at is not None
        assert isinstance(entity.completed_at, datetime)

    def test_processing_duration_seconds(self):
        """Test calculating processing duration."""
        entity = LLMProcessingHistory(
            processing_type=ProcessingType.SPEECH_EXTRACTION,
            model_name="gemini-2.0-flash",
            model_version="2.0.0",
            prompt_template="Extract speeches",
            prompt_variables={},
            input_reference_type="minutes",
            input_reference_id=202,
        )

        # No duration when not started
        assert entity.processing_duration_seconds is None

        # No duration when only started
        entity.start_processing()
        assert entity.processing_duration_seconds is None

        # Has duration when completed
        entity.complete_processing({"speeches": []})
        duration = entity.processing_duration_seconds
        assert duration is not None
        assert duration >= 0
        assert isinstance(duration, float)

    def test_string_representation(self):
        """Test string representation of entity."""
        entity = LLMProcessingHistory(
            processing_type=ProcessingType.PARLIAMENTARY_GROUP_EXTRACTION,
            model_name="gemini-1.5-flash",
            model_version="1.5.0",
            prompt_template="Extract groups",
            prompt_variables={},
            input_reference_type="conference",
            input_reference_id=303,
            status=ProcessingStatus.COMPLETED,
        )

        str_repr = str(entity)
        assert "LLMProcessingHistory" in str_repr
        assert "parliamentary_group_extraction" in str_repr
        assert "gemini-1.5-flash" in str_repr
        assert "completed" in str_repr

    def test_entity_with_id(self):
        """Test creating entity with ID."""
        entity = LLMProcessingHistory(
            processing_type=ProcessingType.MINUTES_DIVISION,
            model_name="gemini-2.0-flash",
            model_version="2.0.0",
            prompt_template="Template",
            prompt_variables={},
            input_reference_type="meeting",
            input_reference_id=404,
            id=999,
        )

        assert entity.id == 999

    def test_all_processing_types(self):
        """Test all processing type enum values."""
        for processing_type in ProcessingType:
            entity = LLMProcessingHistory(
                processing_type=processing_type,
                model_name="test-model",
                model_version="1.0.0",
                prompt_template="test",
                prompt_variables={},
                input_reference_type="test",
                input_reference_id=1,
            )
            assert entity.processing_type == processing_type

    def test_all_processing_statuses(self):
        """Test all processing status enum values."""
        for status in ProcessingStatus:
            entity = LLMProcessingHistory(
                processing_type=ProcessingType.MINUTES_DIVISION,
                model_name="test-model",
                model_version="1.0.0",
                prompt_template="test",
                prompt_variables={},
                input_reference_type="test",
                input_reference_id=1,
                status=status,
            )
            assert entity.status == status

    def test_token_count_properties(self):
        """Test token count and processing time properties."""
        entity = LLMProcessingHistory(
            processing_type=ProcessingType.MINUTES_DIVISION,
            model_name="gemini-2.0-flash",
            model_version="2.0.0",
            prompt_template="test",
            prompt_variables={},
            input_reference_type="meeting",
            input_reference_id=1,
            processing_metadata={
                "token_count_input": 100,
                "token_count_output": 200,
                "processing_time_ms": 1500,
            },
        )

        assert entity.token_count_input == 100
        assert entity.token_count_output == 200
        assert entity.processing_time_ms == 1500

    def test_default_created_by(self):
        """Test default value for created_by field."""
        entity = LLMProcessingHistory(
            processing_type=ProcessingType.SPEAKER_MATCHING,
            model_name="gemini-2.0-flash",
            model_version="2.0.0",
            prompt_template="Match speaker",
            prompt_variables={},
            input_reference_type="speaker",
            input_reference_id=456,
        )

        assert entity.created_by == "system"
