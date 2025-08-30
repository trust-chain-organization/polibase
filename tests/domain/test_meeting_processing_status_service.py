"""Tests for MeetingProcessingStatusService."""

from unittest.mock import AsyncMock

import pytest

from src.domain.entities.conversation import Conversation
from src.domain.entities.minutes import Minutes
from src.domain.services.meeting_processing_status_service import (
    MeetingProcessingStatusService,
)


class TestMeetingProcessingStatusService:
    """Test cases for MeetingProcessingStatusService."""

    @pytest.fixture
    def mock_minutes_repository(self):
        """Create mock minutes repository."""
        return AsyncMock()

    @pytest.fixture
    def mock_conversation_repository(self):
        """Create mock conversation repository."""
        return AsyncMock()

    @pytest.fixture
    def mock_speaker_repository(self):
        """Create mock speaker repository."""
        return AsyncMock()

    @pytest.fixture
    def service(
        self,
        mock_minutes_repository,
        mock_conversation_repository,
        mock_speaker_repository,
    ):
        """Create MeetingProcessingStatusService instance."""
        return MeetingProcessingStatusService(
            minutes_repository=mock_minutes_repository,
            conversation_repository=mock_conversation_repository,
            speaker_repository=mock_speaker_repository,
        )

    @pytest.fixture
    def sample_minutes(self):
        """Create sample minutes."""
        return Minutes(
            id=1,
            meeting_id=1,
            url="https://example.com/minutes1.pdf",
        )

    @pytest.fixture
    def sample_conversations_with_speakers(self):
        """Create sample conversations with speakers."""
        return [
            Conversation(
                id=1,
                comment="これは最初の発言です。",
                sequence_number=1,
                minutes_id=1,
                speaker_id=10,
                speaker_name="山田太郎",
                chapter_number=1,
            ),
            Conversation(
                id=2,
                comment="これは二番目の発言です。",
                sequence_number=2,
                minutes_id=1,
                speaker_id=11,
                speaker_name="鈴木花子",
                chapter_number=1,
            ),
        ]

    @pytest.fixture
    def sample_conversations_without_speakers(self):
        """Create sample conversations without speakers."""
        return [
            Conversation(
                id=1,
                comment="これは最初の発言です。",
                sequence_number=1,
                minutes_id=1,
                speaker_id=None,
                speaker_name="山田太郎",
                chapter_number=1,
            ),
            Conversation(
                id=2,
                comment="これは二番目の発言です。",
                sequence_number=2,
                minutes_id=1,
                speaker_id=None,
                speaker_name="鈴木花子",
                chapter_number=1,
            ),
        ]

    @pytest.mark.asyncio
    async def test_has_conversations_true(
        self,
        service,
        mock_minutes_repository,
        mock_conversation_repository,
        sample_minutes,
        sample_conversations_with_speakers,
    ):
        """Test has_conversations returns True when conversations exist."""
        mock_minutes_repository.get_by_meeting.return_value = sample_minutes
        mock_conversation_repository.get_by_minutes.return_value = (
            sample_conversations_with_speakers
        )

        result = await service.has_conversations(meeting_id=1)

        assert result is True
        mock_minutes_repository.get_by_meeting.assert_called_once_with(1)
        mock_conversation_repository.get_by_minutes.assert_called()

    @pytest.mark.asyncio
    async def test_has_conversations_false_no_minutes(
        self,
        service,
        mock_minutes_repository,
    ):
        """Test has_conversations returns False when no minutes exist."""
        mock_minutes_repository.get_by_meeting.return_value = None

        result = await service.has_conversations(meeting_id=1)

        assert result is False
        mock_minutes_repository.get_by_meeting.assert_called_once_with(1)

    @pytest.mark.asyncio
    async def test_has_conversations_false_no_conversations(
        self,
        service,
        mock_minutes_repository,
        mock_conversation_repository,
        sample_minutes,
    ):
        """Test has_conversations returns False when no conversations exist."""
        mock_minutes_repository.get_by_meeting.return_value = sample_minutes
        mock_conversation_repository.get_by_minutes.return_value = []

        result = await service.has_conversations(meeting_id=1)

        assert result is False
        mock_minutes_repository.get_by_meeting.assert_called_once_with(1)
        mock_conversation_repository.get_by_minutes.assert_called()

    @pytest.mark.asyncio
    async def test_has_speakers_true(
        self,
        service,
        mock_minutes_repository,
        mock_conversation_repository,
        sample_minutes,
        sample_conversations_with_speakers,
    ):
        """Test has_speakers returns True when speakers exist."""
        mock_minutes_repository.get_by_meeting.return_value = sample_minutes
        mock_conversation_repository.get_by_minutes.return_value = (
            sample_conversations_with_speakers
        )

        result = await service.has_speakers(meeting_id=1)

        assert result is True
        mock_minutes_repository.get_by_meeting.assert_called_once_with(1)
        mock_conversation_repository.get_by_minutes.assert_called()

    @pytest.mark.asyncio
    async def test_has_speakers_false_no_speaker_ids(
        self,
        service,
        mock_minutes_repository,
        mock_conversation_repository,
        sample_minutes,
        sample_conversations_without_speakers,
    ):
        """Test has_speakers returns False when no speaker_ids exist."""
        mock_minutes_repository.get_by_meeting.return_value = sample_minutes
        mock_conversation_repository.get_by_minutes.return_value = (
            sample_conversations_without_speakers
        )

        result = await service.has_speakers(meeting_id=1)

        assert result is False
        mock_minutes_repository.get_by_meeting.assert_called_once_with(1)
        mock_conversation_repository.get_by_minutes.assert_called()

    @pytest.mark.asyncio
    async def test_get_processing_status_full(
        self,
        service,
        mock_minutes_repository,
        mock_conversation_repository,
        sample_minutes,
        sample_conversations_with_speakers,
    ):
        """Test get_processing_status with full processing."""
        mock_minutes_repository.get_by_meeting.return_value = sample_minutes
        mock_conversation_repository.get_by_minutes.return_value = (
            sample_conversations_with_speakers
        )

        result = await service.get_processing_status(meeting_id=1)

        assert result["has_minutes"] is True
        assert result["has_conversations"] is True
        assert result["has_speakers"] is True
        assert result["conversation_count"] == 2  # 2 conversations
        assert result["speaker_count"] == 2  # 2 unique speakers

    @pytest.mark.asyncio
    async def test_get_processing_status_no_minutes(
        self,
        service,
        mock_minutes_repository,
    ):
        """Test get_processing_status when no minutes exist."""
        mock_minutes_repository.get_by_meeting.return_value = None

        result = await service.get_processing_status(meeting_id=1)

        assert result["has_minutes"] is False
        assert result["has_conversations"] is False
        assert result["has_speakers"] is False
        assert result["conversation_count"] == 0
        assert result["speaker_count"] == 0

    @pytest.mark.asyncio
    async def test_get_processing_status_conversations_no_speakers(
        self,
        service,
        mock_minutes_repository,
        mock_conversation_repository,
        sample_minutes,
        sample_conversations_without_speakers,
    ):
        """Test get_processing_status with conversations but no speakers."""
        mock_minutes_repository.get_by_meeting.return_value = sample_minutes
        mock_conversation_repository.get_by_minutes.return_value = (
            sample_conversations_without_speakers
        )

        result = await service.get_processing_status(meeting_id=1)

        assert result["has_minutes"] is True
        assert result["has_conversations"] is True
        assert result["has_speakers"] is False
        assert result["conversation_count"] == 2  # 2 conversations
        assert result["speaker_count"] == 0

    @pytest.mark.asyncio
    async def test_cache_functionality(
        self,
        service,
        mock_minutes_repository,
        mock_conversation_repository,
        sample_minutes,
        sample_conversations_with_speakers,
    ):
        """Test cache functionality."""
        mock_minutes_repository.get_by_meeting.return_value = sample_minutes
        mock_conversation_repository.get_by_minutes.return_value = (
            sample_conversations_with_speakers
        )

        # First call - should hit repositories
        result1 = await service.get_processing_status(meeting_id=1)
        assert mock_minutes_repository.get_by_meeting.call_count == 1

        # Second call - should use cache
        result2 = await service.get_processing_status(meeting_id=1)
        assert mock_minutes_repository.get_by_meeting.call_count == 1  # Still 1

        # Results should be the same
        assert result1 == result2

        # Clear cache
        service.clear_cache(meeting_id=1)

        # Third call - should hit repositories again
        await service.get_processing_status(meeting_id=1)
        assert mock_minutes_repository.get_by_meeting.call_count == 2

    def test_clear_cache_all(self, service: MeetingProcessingStatusService) -> None:
        """Test clearing entire cache."""
        # Add some items to cache
        service._cache[1] = {
            "has_minutes": True,
            "has_conversations": True,
            "has_speakers": True,
            "conversation_count": 10,
            "speaker_count": 5,
        }
        service._cache[2] = {
            "has_minutes": True,
            "has_conversations": False,
            "has_speakers": False,
            "conversation_count": 0,
            "speaker_count": 0,
        }

        assert len(service._cache) == 2

        # Clear all cache
        service.clear_cache()

        assert len(service._cache) == 0

    def test_clear_cache_specific(
        self, service: MeetingProcessingStatusService
    ) -> None:
        """Test clearing specific cache entry."""
        # Add some items to cache
        service._cache[1] = {
            "has_minutes": True,
            "has_conversations": True,
            "has_speakers": True,
            "conversation_count": 10,
            "speaker_count": 5,
        }
        service._cache[2] = {
            "has_minutes": True,
            "has_conversations": False,
            "has_speakers": False,
            "conversation_count": 0,
            "speaker_count": 0,
        }

        assert len(service._cache) == 2

        # Clear specific cache entry
        service.clear_cache(meeting_id=1)

        assert len(service._cache) == 1
        assert 1 not in service._cache
        assert 2 in service._cache
