"""Tests for sync_speaker_extractor module"""

from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch

from src.application.usecases.execute_speaker_extraction_usecase import (
    SpeakerExtractionResultDTO,
)
from src.streamlit.utils.sync_speaker_extractor import (
    SyncSpeakerExtractionResult,
    SyncSpeakerExtractor,
)


class TestSyncSpeakerExtractor:
    """Test cases for SyncSpeakerExtractor"""

    def test_process_success(self):
        """Test successful speaker extraction process"""
        # Arrange
        meeting_id = 1
        extractor = SyncSpeakerExtractor(meeting_id)

        # Mock use case result
        mock_result = SpeakerExtractionResultDTO(
            meeting_id=meeting_id,
            total_conversations=10,
            unique_speakers=5,
            new_speakers=3,
            existing_speakers=2,
            processing_time_seconds=1.5,
            processed_at=datetime.now(),
            errors=None,
        )

        # Mock use case
        mock_usecase = Mock()
        mock_usecase.execute = AsyncMock(return_value=mock_result)

        # Mock container
        mock_container = Mock()
        mock_container.use_cases.speaker_extraction_usecase.return_value = mock_usecase

        # Act
        with patch(
            "src.streamlit.utils.sync_speaker_extractor.get_container",
            return_value=mock_container,
        ):
            result = extractor.process()

        # Assert
        assert isinstance(result, SyncSpeakerExtractionResult)
        assert result.meeting_id == meeting_id
        assert result.total_conversations == 10
        assert result.unique_speakers == 5
        assert result.new_speakers == 3
        assert result.existing_speakers == 2
        assert result.errors is None

    def test_process_with_error(self):
        """Test speaker extraction with error handling"""
        # Arrange
        meeting_id = 1
        extractor = SyncSpeakerExtractor(meeting_id)

        # Mock use case that raises an error
        mock_usecase = Mock()
        mock_usecase.execute = AsyncMock(
            side_effect=ValueError("No conversations found")
        )

        # Mock container
        mock_container = Mock()
        mock_container.use_cases.speaker_extraction_usecase.return_value = mock_usecase

        # Act
        with patch(
            "src.streamlit.utils.sync_speaker_extractor.get_container",
            return_value=mock_container,
        ):
            result = extractor.process()

        # Assert
        assert isinstance(result, SyncSpeakerExtractionResult)
        assert result.meeting_id == meeting_id
        assert result.errors is not None
        assert len(result.errors) == 1
        assert "No conversations found" in result.errors[0]
        # When error occurs, stats should be zero
        assert result.total_conversations == 0
        assert result.unique_speakers == 0
        assert result.new_speakers == 0

    def test_process_container_not_initialized(self):
        """Test that container is initialized if not available"""
        # Arrange
        meeting_id = 1
        extractor = SyncSpeakerExtractor(meeting_id)

        # Mock use case result
        mock_result = SpeakerExtractionResultDTO(
            meeting_id=meeting_id,
            total_conversations=5,
            unique_speakers=3,
            new_speakers=2,
            existing_speakers=1,
            processing_time_seconds=1.0,
            processed_at=datetime.now(),
            errors=None,
        )

        # Mock use case
        mock_usecase = Mock()
        mock_usecase.execute = AsyncMock(return_value=mock_result)

        # Mock container
        mock_container = Mock()
        mock_container.use_cases.speaker_extraction_usecase.return_value = mock_usecase

        # Mock get_container to raise RuntimeError first time (not initialized)
        # Then init_container returns the container
        with patch(
            "src.streamlit.utils.sync_speaker_extractor.get_container",
            side_effect=RuntimeError("Container not initialized"),
        ):
            with patch(
                "src.streamlit.utils.sync_speaker_extractor.init_container",
                return_value=mock_container,
            ):
                # Act
                result = extractor.process()

                # Assert
                assert isinstance(result, SyncSpeakerExtractionResult)
                assert result.meeting_id == meeting_id
                assert result.total_conversations == 5

    def test_process_with_existing_speakers(self):
        """Test speaker extraction when some speakers already exist"""
        # Arrange
        meeting_id = 1
        extractor = SyncSpeakerExtractor(meeting_id)

        # Mock use case result with existing speakers
        mock_result = SpeakerExtractionResultDTO(
            meeting_id=meeting_id,
            total_conversations=20,
            unique_speakers=8,
            new_speakers=3,  # Only 3 new speakers
            existing_speakers=5,  # 5 already existed
            processing_time_seconds=2.0,
            processed_at=datetime.now(),
            errors=None,
        )

        # Mock use case
        mock_usecase = Mock()
        mock_usecase.execute = AsyncMock(return_value=mock_result)

        # Mock container
        mock_container = Mock()
        mock_container.use_cases.speaker_extraction_usecase.return_value = mock_usecase

        # Act
        with patch(
            "src.streamlit.utils.sync_speaker_extractor.get_container",
            return_value=mock_container,
        ):
            result = extractor.process()

        # Assert
        assert result.new_speakers == 3
        assert result.existing_speakers == 5
        assert result.unique_speakers == 8
