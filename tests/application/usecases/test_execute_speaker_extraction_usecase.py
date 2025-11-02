"""Tests for ExecuteSpeakerExtractionUseCase."""

from datetime import datetime
from unittest.mock import AsyncMock

import pytest

from src.application.usecases.execute_speaker_extraction_usecase import (
    ExecuteSpeakerExtractionDTO,
    ExecuteSpeakerExtractionUseCase,
    SpeakerExtractionResultDTO,
)
from src.domain.entities.conversation import Conversation
from src.domain.entities.minutes import Minutes
from src.domain.entities.speaker import Speaker


class TestExecuteSpeakerExtractionUseCase:
    """Test cases for ExecuteSpeakerExtractionUseCase."""

    @pytest.fixture
    def mock_minutes_repository(self):
        """Create mock minutes repository."""
        repo = AsyncMock()
        return repo

    @pytest.fixture
    def mock_conversation_repository(self):
        """Create mock conversation repository."""
        repo = AsyncMock()
        return repo

    @pytest.fixture
    def mock_speaker_repository(self):
        """Create mock speaker repository."""
        repo = AsyncMock()
        return repo

    @pytest.fixture
    def mock_speaker_domain_service(self):
        """Create mock speaker domain service."""
        from unittest.mock import MagicMock

        service = MagicMock()
        # Default behavior: return name as-is with no party
        service.extract_party_from_name.return_value = ("山田太郎", None)
        return service

    @pytest.fixture
    def use_case(
        self,
        mock_minutes_repository,
        mock_conversation_repository,
        mock_speaker_repository,
        mock_speaker_domain_service,
    ):
        """Create ExecuteSpeakerExtractionUseCase instance."""
        return ExecuteSpeakerExtractionUseCase(
            minutes_repository=mock_minutes_repository,
            conversation_repository=mock_conversation_repository,
            speaker_repository=mock_speaker_repository,
            speaker_domain_service=mock_speaker_domain_service,
        )

    @pytest.fixture
    def sample_minutes(self):
        """Create a sample minutes entity."""
        return Minutes(
            id=1,
            meeting_id=1,
            url="https://example.com/minutes",
            processed_at=datetime.now(),
        )

    @pytest.fixture
    def sample_conversations(self):
        """Create sample conversation entities."""
        return [
            Conversation(
                id=1,
                minutes_id=1,
                speaker_name="山田太郎",
                comment="発言内容1",
                sequence_number=1,
            ),
            Conversation(
                id=2,
                minutes_id=1,
                speaker_name="鈴木花子",
                comment="発言内容2",
                sequence_number=2,
            ),
            Conversation(
                id=3,
                minutes_id=1,
                speaker_name="山田太郎",
                comment="発言内容3",
                sequence_number=3,
            ),
        ]

    @pytest.mark.asyncio
    async def test_execute_speaker_extraction_success(
        self,
        use_case,
        mock_minutes_repository,
        mock_conversation_repository,
        mock_speaker_repository,
        mock_speaker_domain_service,
        sample_minutes,
        sample_conversations,
    ):
        """Test successful speaker extraction from conversations."""
        # Arrange
        mock_minutes_repository.get_by_meeting.return_value = sample_minutes
        mock_conversation_repository.get_by_minutes.return_value = sample_conversations
        mock_speaker_repository.get_by_name_party_position.return_value = None

        # Mock speaker domain service to extract different speakers
        def extract_party_side_effect(name):
            if "山田" in name:
                return ("山田太郎", None)
            elif "鈴木" in name:
                return ("鈴木花子", None)
            return (name, None)

        mock_speaker_domain_service.extract_party_from_name.side_effect = (
            extract_party_side_effect
        )

        created_speakers = [
            Speaker(id=1, name="山田太郎", is_politician=False),
            Speaker(id=2, name="鈴木花子", is_politician=False),
        ]
        mock_speaker_repository.create.side_effect = created_speakers

        request = ExecuteSpeakerExtractionDTO(meeting_id=1, force_reprocess=False)

        # Act
        result = await use_case.execute(request)

        # Assert
        assert isinstance(result, SpeakerExtractionResultDTO)
        assert result.meeting_id == 1
        assert result.total_conversations == 3
        assert result.unique_speakers == 2
        assert result.new_speakers == 2
        assert result.existing_speakers == 0
        assert result.errors is None or len(result.errors) == 0
        mock_minutes_repository.get_by_meeting.assert_called_once_with(1)
        assert mock_speaker_repository.create.call_count == 2
        assert mock_conversation_repository.update.call_count == 3

    @pytest.mark.asyncio
    async def test_execute_no_minutes_found(self, use_case, mock_minutes_repository):
        """Test extraction when minutes do not exist."""
        # Arrange
        mock_minutes_repository.get_by_meeting.return_value = None

        request = ExecuteSpeakerExtractionDTO(meeting_id=999)

        # Act & Assert
        with pytest.raises(ValueError, match="No minutes found for meeting 999"):
            await use_case.execute(request)

        mock_minutes_repository.get_by_meeting.assert_called_once_with(999)

    @pytest.mark.asyncio
    async def test_execute_no_conversations_found(
        self,
        use_case,
        mock_minutes_repository,
        mock_conversation_repository,
        sample_minutes,
    ):
        """Test extraction when no conversations exist."""
        # Arrange
        mock_minutes_repository.get_by_meeting.return_value = sample_minutes
        mock_conversation_repository.get_by_minutes.return_value = []

        request = ExecuteSpeakerExtractionDTO(meeting_id=1)

        # Act & Assert
        with pytest.raises(ValueError, match="No conversations found for meeting 1"):
            await use_case.execute(request)

    @pytest.mark.asyncio
    async def test_execute_already_linked_no_force(
        self,
        use_case,
        mock_minutes_repository,
        mock_conversation_repository,
        sample_minutes,
    ):
        """Test extraction when conversations already have speakers without force
        reprocess."""
        # Arrange
        conversations_with_speakers = [
            Conversation(
                id=1,
                minutes_id=1,
                speaker_id=10,
                speaker_name="山田太郎",
                comment="発言内容",
                sequence_number=1,
            ),
        ]
        mock_minutes_repository.get_by_meeting.return_value = sample_minutes
        mock_conversation_repository.get_by_minutes.return_value = (
            conversations_with_speakers
        )

        request = ExecuteSpeakerExtractionDTO(meeting_id=1, force_reprocess=False)

        # Act & Assert
        with pytest.raises(
            ValueError, match="already has .* conversations with speakers"
        ):
            await use_case.execute(request)

    @pytest.mark.asyncio
    async def test_execute_force_reprocess_clears_existing_links(
        self,
        use_case,
        mock_minutes_repository,
        mock_conversation_repository,
        mock_speaker_repository,
        mock_speaker_domain_service,
        sample_minutes,
    ):
        """Test force reprocessing clears existing speaker links."""
        # Arrange
        conversations_with_speakers = [
            Conversation(
                id=1,
                minutes_id=1,
                speaker_id=10,
                speaker_name="山田太郎",
                comment="発言内容",
                sequence_number=1,
            ),
        ]
        mock_minutes_repository.get_by_meeting.return_value = sample_minutes
        mock_conversation_repository.get_by_minutes.return_value = (
            conversations_with_speakers
        )
        mock_speaker_repository.get_by_name_party_position.return_value = None
        mock_speaker_repository.create.return_value = Speaker(
            id=1, name="山田太郎", is_politician=False
        )

        request = ExecuteSpeakerExtractionDTO(meeting_id=1, force_reprocess=True)

        # Act
        result = await use_case.execute(request)

        # Assert
        assert result.meeting_id == 1
        # Verify that speaker_id was cleared (updated twice: once to clear, once
        # to link)
        assert mock_conversation_repository.update.call_count == 2

    @pytest.mark.asyncio
    async def test_execute_use_existing_speaker(
        self,
        use_case,
        mock_minutes_repository,
        mock_conversation_repository,
        mock_speaker_repository,
        sample_minutes,
        sample_conversations,
    ):
        """Test using existing speaker instead of creating new one."""
        # Arrange
        mock_minutes_repository.get_by_meeting.return_value = sample_minutes
        mock_conversation_repository.get_by_minutes.return_value = sample_conversations
        existing_speaker = Speaker(id=5, name="山田太郎", is_politician=False)
        mock_speaker_repository.get_by_name_party_position.return_value = (
            existing_speaker
        )

        request = ExecuteSpeakerExtractionDTO(meeting_id=1)

        # Act
        result = await use_case.execute(request)

        # Assert
        assert result.new_speakers == 0
        assert result.existing_speakers >= 1
        mock_speaker_repository.create.assert_not_called()

    @pytest.mark.asyncio
    async def test_execute_extract_party_from_name(
        self,
        use_case,
        mock_minutes_repository,
        mock_conversation_repository,
        mock_speaker_repository,
        mock_speaker_domain_service,
        sample_minutes,
    ):
        """Test extracting party information from speaker names."""
        # Arrange
        conversations_with_party = [
            Conversation(
                id=1,
                minutes_id=1,
                speaker_name="山田太郎（自民党）",
                comment="発言内容",
                sequence_number=1,
            ),
        ]
        mock_minutes_repository.get_by_meeting.return_value = sample_minutes
        mock_conversation_repository.get_by_minutes.return_value = (
            conversations_with_party
        )
        mock_speaker_domain_service.extract_party_from_name.return_value = (
            "山田太郎",
            "自民党",
        )
        mock_speaker_repository.get_by_name_party_position.return_value = None
        mock_speaker_repository.create.return_value = Speaker(
            id=1, name="山田太郎", political_party_name="自民党", is_politician=True
        )

        request = ExecuteSpeakerExtractionDTO(meeting_id=1)

        # Act
        result = await use_case.execute(request)

        # Assert
        assert result.new_speakers == 1
        # Verify that speaker was created with party info
        create_call = mock_speaker_repository.create.call_args[0][0]
        assert create_call.political_party_name == "自民党"
        assert create_call.is_politician is True

    @pytest.mark.asyncio
    async def test_execute_multiple_unique_speakers(
        self,
        use_case,
        mock_minutes_repository,
        mock_conversation_repository,
        mock_speaker_repository,
        mock_speaker_domain_service,
        sample_minutes,
    ):
        """Test extraction with multiple unique speakers."""
        # Arrange
        conversations = [
            Conversation(
                comment=f"発言{i}",
                sequence_number=i,
                id=i,
                minutes_id=1,
                speaker_name=f"議員{i}",
            )
            for i in range(1, 6)
        ]
        mock_minutes_repository.get_by_meeting.return_value = sample_minutes
        mock_conversation_repository.get_by_minutes.return_value = conversations

        def extract_side_effect(name):
            return (name, None)

        mock_speaker_domain_service.extract_party_from_name.side_effect = (
            extract_side_effect
        )
        mock_speaker_repository.get_by_name_party_position.return_value = None
        mock_speaker_repository.create.side_effect = [
            Speaker(id=i, name=f"議員{i}", is_politician=False) for i in range(1, 6)
        ]

        request = ExecuteSpeakerExtractionDTO(meeting_id=1)

        # Act
        result = await use_case.execute(request)

        # Assert
        assert result.unique_speakers == 5
        assert result.new_speakers == 5
        assert mock_speaker_repository.create.call_count == 5

    @pytest.mark.asyncio
    async def test_execute_processing_time_recorded(
        self,
        use_case,
        mock_minutes_repository,
        mock_conversation_repository,
        mock_speaker_repository,
        sample_minutes,
        sample_conversations,
    ):
        """Test that processing time is properly recorded."""
        # Arrange
        mock_minutes_repository.get_by_meeting.return_value = sample_minutes
        mock_conversation_repository.get_by_minutes.return_value = sample_conversations
        mock_speaker_repository.get_by_name_party_position.return_value = None
        mock_speaker_repository.create.return_value = Speaker(
            id=1, name="山田太郎", is_politician=False
        )

        request = ExecuteSpeakerExtractionDTO(meeting_id=1)

        # Act
        result = await use_case.execute(request)

        # Assert
        assert result.processing_time_seconds >= 0
        assert isinstance(result.processed_at, datetime)

    @pytest.mark.asyncio
    async def test_execute_link_conversations_to_speakers(
        self,
        use_case,
        mock_minutes_repository,
        mock_conversation_repository,
        mock_speaker_repository,
        mock_speaker_domain_service,
        sample_minutes,
        sample_conversations,
    ):
        """Test that conversations are properly linked to speakers."""
        # Arrange
        mock_minutes_repository.get_by_meeting.return_value = sample_minutes
        mock_conversation_repository.get_by_minutes.return_value = sample_conversations

        def extract_party_side_effect(name):
            if "山田" in name:
                return ("山田太郎", None)
            elif "鈴木" in name:
                return ("鈴木花子", None)
            return (name, None)

        mock_speaker_domain_service.extract_party_from_name.side_effect = (
            extract_party_side_effect
        )
        mock_speaker_repository.get_by_name_party_position.return_value = None
        mock_speaker_repository.create.side_effect = [
            Speaker(id=1, name="山田太郎", is_politician=False),
            Speaker(id=2, name="鈴木花子", is_politician=False),
        ]

        request = ExecuteSpeakerExtractionDTO(meeting_id=1)

        # Act
        result = await use_case.execute(request)

        # Assert
        # All 3 conversations should be updated with speaker_id
        assert mock_conversation_repository.update.call_count == 3
        assert result.total_conversations == 3
