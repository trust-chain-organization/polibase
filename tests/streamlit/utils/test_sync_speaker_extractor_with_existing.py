"""Tests for sync_speaker_extractor module - with existing speakers"""

from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch

from src.application.usecases.execute_speaker_extraction_usecase import (
    SpeakerExtractionResultDTO,
)
from src.streamlit.utils.sync_speaker_extractor import SyncSpeakerExtractor


class TestSyncSpeakerExtractorWithExisting:
    """Test cases for SyncSpeakerExtractor with existing speakers"""

    def test_extract_and_link_existing_speakers(self):
        """Test linking conversations to existing speakers"""
        # Arrange
        meeting_id = 1
        extractor = SyncSpeakerExtractor(meeting_id)

        # Mock use case result - no new speakers, all existing
        mock_result = SpeakerExtractionResultDTO(
            meeting_id=meeting_id,
            total_conversations=2,
            unique_speakers=2,
            new_speakers=0,  # No new speakers created
            existing_speakers=2,  # Both speakers already exist
            processing_time_seconds=0.5,
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
        assert result.unique_speakers == 2
        assert result.new_speakers == 0  # No new speakers
        assert result.existing_speakers == 2  # All existing
        assert result.errors is None
