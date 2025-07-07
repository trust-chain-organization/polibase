"""Tests for ProcessMinutesUseCase."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.application.dtos.minutes_dto import ProcessMinutesDTO
from src.application.usecases.process_minutes_usecase import ProcessMinutesUseCase
from src.domain.entities.conversation import Conversation
from src.domain.entities.meeting import Meeting
from src.domain.entities.minutes import Minutes
from src.domain.entities.speaker import Speaker


class TestProcessMinutesUseCase:
    """Test cases for ProcessMinutesUseCase."""

    @pytest.fixture
    def mock_meeting_repo(self):
        """Create mock meeting repository."""
        repo = AsyncMock()
        return repo

    @pytest.fixture
    def mock_minutes_repo(self):
        """Create mock minutes repository."""
        repo = AsyncMock()
        return repo

    @pytest.fixture
    def mock_conversation_repo(self):
        """Create mock conversation repository."""
        repo = AsyncMock()
        return repo

    @pytest.fixture
    def mock_speaker_repo(self):
        """Create mock speaker repository."""
        repo = AsyncMock()
        return repo

    @pytest.fixture
    def mock_minutes_service(self):
        """Create mock minutes domain service."""
        service = MagicMock()
        service.is_minutes_processed.return_value = False
        service.calculate_processing_duration.return_value = 5.0
        return service

    @pytest.fixture
    def mock_speaker_service(self):
        """Create mock speaker domain service."""
        service = MagicMock()
        service.extract_party_from_name.return_value = ("山田太郎", "自民党")
        return service

    @pytest.fixture
    def mock_pdf_processor(self):
        """Create mock PDF processor."""
        processor = AsyncMock()
        return processor

    @pytest.fixture
    def mock_text_extractor(self):
        """Create mock text extractor."""
        extractor = AsyncMock()
        return extractor

    @pytest.fixture
    def use_case(
        self,
        mock_meeting_repo,
        mock_minutes_repo,
        mock_conversation_repo,
        mock_speaker_repo,
        mock_minutes_service,
        mock_speaker_service,
        mock_pdf_processor,
        mock_text_extractor,
    ):
        """Create ProcessMinutesUseCase instance."""
        return ProcessMinutesUseCase(
            meeting_repository=mock_meeting_repo,
            minutes_repository=mock_minutes_repo,
            conversation_repository=mock_conversation_repo,
            speaker_repository=mock_speaker_repo,
            minutes_domain_service=mock_minutes_service,
            speaker_domain_service=mock_speaker_service,
            pdf_processor=mock_pdf_processor,
            text_extractor=mock_text_extractor,
        )

    @pytest.mark.asyncio
    async def test_execute_success_with_pdf(
        self,
        use_case,
        mock_meeting_repo,
        mock_minutes_repo,
        mock_conversation_repo,
        mock_speaker_repo,
        mock_minutes_service,
        mock_speaker_service,
        mock_pdf_processor,
    ):
        """Test successful minutes processing from PDF."""
        # Setup
        meeting = Meeting(
            id=1,
            conference_id=1,
            date="2023-01-01",
            url="test.pdf",
            gcs_pdf_uri="gs://bucket/test.pdf",
        )
        request = ProcessMinutesDTO(meeting_id=1)

        mock_meeting_repo.get_by_id.return_value = meeting
        mock_minutes_repo.get_by_meeting.return_value = None
        mock_minutes_repo.create.return_value = Minutes(
            id=10, meeting_id=1, url="test.pdf"
        )

        mock_pdf_processor.process_pdf.return_value = [
            {"speaker": "山田太郎", "content": "発言内容1"},
            {"speaker": "鈴木花子", "content": "発言内容2"},
        ]

        conversations = [
            Conversation(
                id=1,
                comment="発言内容1",
                sequence_number=1,
                minutes_id=10,
                speaker_name="山田太郎",
                chapter_number=1,
            ),
            Conversation(
                id=2,
                comment="発言内容2",
                sequence_number=2,
                minutes_id=10,
                speaker_name="鈴木花子",
                chapter_number=1,
            ),
        ]
        mock_minutes_service.create_conversations_from_speeches.return_value = (
            conversations
        )
        mock_conversation_repo.bulk_create.return_value = conversations

        mock_speaker_repo.get_by_name_party_position.return_value = None
        mock_speaker_repo.create.side_effect = [
            Speaker(id=1, name="山田太郎", is_politician=True),
            Speaker(id=2, name="鈴木花子", is_politician=True),
        ]

        # Set up speaker service to return different names for each call
        mock_speaker_service.extract_party_from_name.side_effect = [
            ("山田太郎", "自民党"),
            ("鈴木花子", "公明党"),
        ]

        # Execute
        result = await use_case.execute(request)

        # Verify
        assert result.minutes_id == 10
        assert result.meeting_id == 1
        assert result.total_conversations == 2
        assert result.unique_speakers == 2
        assert result.processing_time_seconds == 5.0
        assert result.errors is None

        # Verify repository calls
        mock_minutes_repo.create.assert_called_once()
        mock_conversation_repo.bulk_create.assert_called_once()
        mock_minutes_repo.mark_processed.assert_called_once_with(10)

    @pytest.mark.asyncio
    async def test_execute_with_existing_processed_minutes(
        self, use_case, mock_meeting_repo, mock_minutes_repo, mock_minutes_service
    ):
        """Test error when minutes are already processed."""
        # Setup
        meeting = Meeting(id=1, conference_id=1, date="2023-01-01")
        existing_minutes = Minutes(id=10, meeting_id=1, url="test.pdf")
        request = ProcessMinutesDTO(meeting_id=1, force_reprocess=False)

        mock_meeting_repo.get_by_id.return_value = meeting
        mock_minutes_repo.get_by_meeting.return_value = existing_minutes
        mock_minutes_service.is_minutes_processed.return_value = True

        # Execute and verify
        with pytest.raises(ValueError) as exc_info:
            await use_case.execute(request)

        assert "already processed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_execute_force_reprocess(
        self,
        use_case,
        mock_meeting_repo,
        mock_minutes_repo,
        mock_minutes_service,
        mock_pdf_processor,
        mock_conversation_repo,
    ):
        """Test force reprocessing of existing minutes."""
        # Setup
        meeting = Meeting(
            id=1, conference_id=1, date="2023-01-01", gcs_pdf_uri="gs://bucket/test.pdf"
        )
        existing_minutes = Minutes(id=10, meeting_id=1, url="test.pdf")
        request = ProcessMinutesDTO(meeting_id=1, force_reprocess=True)

        mock_meeting_repo.get_by_id.return_value = meeting
        mock_minutes_repo.get_by_meeting.return_value = existing_minutes
        mock_minutes_service.is_minutes_processed.return_value = True

        mock_pdf_processor.process_pdf.return_value = []
        mock_minutes_service.create_conversations_from_speeches.return_value = []
        mock_conversation_repo.bulk_create.return_value = []

        # Execute
        result = await use_case.execute(request)

        # Verify
        assert result.minutes_id == 10
        # Should not create new minutes
        mock_minutes_repo.create.assert_not_called()

    @pytest.mark.asyncio
    async def test_execute_meeting_not_found(self, use_case, mock_meeting_repo):
        """Test error when meeting not found."""
        # Setup
        request = ProcessMinutesDTO(meeting_id=999)
        mock_meeting_repo.get_by_id.return_value = None

        # Execute and verify
        with pytest.raises(ValueError) as exc_info:
            await use_case.execute(request)

        assert "Meeting 999 not found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_execute_with_gcs_text(
        self,
        use_case,
        mock_meeting_repo,
        mock_minutes_repo,
        mock_text_extractor,
        mock_conversation_repo,
    ):
        """Test processing from GCS text."""
        # Setup
        meeting = Meeting(id=1, conference_id=1, date="2023-01-01")
        request = ProcessMinutesDTO(meeting_id=1, gcs_text_uri="gs://bucket/text.txt")

        mock_meeting_repo.get_by_id.return_value = meeting
        mock_minutes_repo.get_by_meeting.return_value = None
        mock_minutes_repo.create.return_value = Minutes(
            id=10, meeting_id=1, url=meeting.url
        )

        mock_text_extractor.extract_from_gcs.return_value = "text content"
        mock_text_extractor.parse_speeches.return_value = [
            {"speaker": "山田太郎", "content": "発言内容"},
        ]

        mock_conversation_repo.bulk_create.return_value = []

        # Execute
        await use_case.execute(request)

        # Verify
        mock_text_extractor.extract_from_gcs.assert_called_once_with(
            "gs://bucket/text.txt"
        )
        mock_text_extractor.parse_speeches.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_no_valid_source(
        self, use_case, mock_meeting_repo, mock_minutes_repo
    ):
        """Test error when no valid source is provided."""
        # Setup
        meeting = Meeting(id=1, conference_id=1, date="2023-01-01")
        request = ProcessMinutesDTO(meeting_id=1)

        mock_meeting_repo.get_by_id.return_value = meeting
        mock_minutes_repo.get_by_meeting.return_value = None
        mock_minutes_repo.create.return_value = Minutes(id=10, meeting_id=1, url=None)

        # Execute and verify
        with pytest.raises(ValueError) as exc_info:
            await use_case.execute(request)

        assert "No valid source" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_extract_and_create_speakers(
        self, use_case, mock_speaker_repo, mock_speaker_service
    ):
        """Test speaker extraction and creation."""
        # Setup
        conversations = [
            Conversation(
                comment="発言1",
                sequence_number=1,
                minutes_id=1,
                speaker_name="山田太郎（自民党）",
                chapter_number=1,
            ),
            Conversation(
                comment="発言2",
                sequence_number=2,
                minutes_id=1,
                speaker_name="鈴木花子（公明党）",
                chapter_number=1,
            ),
            Conversation(
                comment="発言3",
                sequence_number=3,
                minutes_id=1,
                speaker_name="山田太郎（自民党）",  # Duplicate
                chapter_number=1,
            ),
        ]

        mock_speaker_service.extract_party_from_name.side_effect = [
            ("山田太郎", "自民党"),
            ("鈴木花子", "公明党"),
            ("山田太郎", "自民党"),
        ]
        mock_speaker_repo.get_by_name_party_position.return_value = None

        # Execute
        created_count = await use_case._extract_and_create_speakers(conversations)

        # Verify
        assert created_count == 2  # Two unique speakers
        assert mock_speaker_repo.create.call_count == 2

    @pytest.mark.asyncio
    async def test_extract_and_create_speakers_existing(
        self, use_case, mock_speaker_repo, mock_speaker_service
    ):
        """Test speaker extraction when speaker already exists."""
        # Setup
        conversations = [
            Conversation(
                comment="発言1",
                sequence_number=1,
                minutes_id=1,
                speaker_name="山田太郎",
                chapter_number=1,
            ),
        ]

        existing_speaker = Speaker(id=1, name="山田太郎", is_politician=True)
        mock_speaker_repo.get_by_name_party_position.return_value = existing_speaker

        # Execute
        created_count = await use_case._extract_and_create_speakers(conversations)

        # Verify
        assert created_count == 0  # No new speakers created
        mock_speaker_repo.create.assert_not_called()
