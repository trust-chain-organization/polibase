"""Tests for MinutesDomainService."""

from datetime import UTC, datetime

import pytest

from src.domain.entities.conversation import Conversation
from src.domain.entities.minutes import Minutes
from src.domain.services.minutes_domain_service import MinutesDomainService


class TestMinutesDomainService:
    """Test cases for MinutesDomainService."""

    @pytest.fixture
    def service(self):
        """Create MinutesDomainService instance."""
        return MinutesDomainService()

    @pytest.fixture
    def sample_conversations(self):
        """Create sample conversations."""
        return [
            Conversation(
                id=1,
                comment="これは最初の発言です。",
                sequence_number=1,
                minutes_id=1,
                speaker_name="山田太郎",
                chapter_number=1,
            ),
            Conversation(
                id=2,
                comment="これは二番目の発言です。",
                sequence_number=2,
                minutes_id=1,
                speaker_name="鈴木花子",
                chapter_number=1,
            ),
        ]

    def test_validate_minutes_url_valid(self, service):
        """Test validation of valid minutes URLs."""
        valid_urls = [
            "https://example.kaigiroku.net/minutes/2023-01-01.pdf",
            "https://example.go.jp/minutes/meeting.html",
            "https://example.lg.jp/council/minutes.htm",
            "https://example.com/minutes.pdf",
            "https://example.com/minutes.PDF",
        ]

        for url in valid_urls:
            assert service.validate_minutes_url(url) is True

    def test_validate_minutes_url_invalid(self, service):
        """Test validation of invalid minutes URLs."""
        invalid_urls = [
            "",
            None,
            "https://example.com/news",
            "https://example.com/image.jpg",
            "https://example.com/data.json",
        ]

        for url in invalid_urls:
            assert service.validate_minutes_url(url) is False

    def test_extract_meeting_info_from_url(self, service):
        """Test extracting meeting info from URL."""
        # Test with date and meeting name
        date, name = service.extract_meeting_info_from_url(
            "https://example.com/2023-04-15/本会議/minutes.pdf"
        )
        assert date == "2023-04-15"
        assert name == "本会議"

        # Test with date only
        date, name = service.extract_meeting_info_from_url(
            "https://example.com/20230415_minutes.pdf"
        )
        assert date == "2023-04-15"
        assert name is None

        # Test with committee name
        date, name = service.extract_meeting_info_from_url(
            "https://example.com/総務委員会/2023_04_15.pdf"
        )
        assert date == "2023-04-15"
        assert name == "総務委員会"

        # Test with no extractable info
        date, name = service.extract_meeting_info_from_url(
            "https://example.com/minutes.pdf"
        )
        assert date is None
        assert name is None

    def test_create_conversations_from_speeches_dict(self, service):
        """Test creating conversations from speech dictionaries."""
        speeches = [
            {"speaker": "山田太郎", "content": "これは最初の発言です。"},
            {"speaker": "鈴木花子", "content": "これは二番目の発言です。"},
            {"speaker": "", "content": "発言者不明の内容"},
            {"speaker": "田中次郎", "content": ""},  # Empty content
        ]

        conversations = service.create_conversations_from_speeches(speeches, 1)

        assert len(conversations) == 3  # Empty content is skipped
        assert conversations[0].speaker_name == "山田太郎"
        assert conversations[0].comment == "これは最初の発言です。"
        assert conversations[0].sequence_number == 1
        assert conversations[0].minutes_id == 1
        assert conversations[0].chapter_number == 1

        assert conversations[1].speaker_name == "鈴木花子"
        assert conversations[1].sequence_number == 2

        assert conversations[2].speaker_name is None  # Empty speaker
        assert conversations[2].sequence_number == 3

    def test_create_conversations_from_speeches_dto(self, service):
        """Test creating conversations from ExtractedSpeechDTO objects."""
        from src.application.dtos.minutes_dto import ExtractedSpeechDTO

        speeches = [
            ExtractedSpeechDTO(
                speaker_name="山田太郎", content="発言内容1", sequence_number=1
            ),
            ExtractedSpeechDTO(
                speaker_name="鈴木花子", content="発言内容2", sequence_number=2
            ),
        ]

        conversations = service.create_conversations_from_speeches(
            speeches, minutes_id=2, chapter_number=3
        )

        assert len(conversations) == 2
        assert conversations[0].speaker_name == "山田太郎"
        assert conversations[0].comment == "発言内容1"
        assert conversations[0].minutes_id == 2
        assert conversations[0].chapter_number == 3

    def test_split_long_conversation(self, service):
        """Test splitting long conversations."""
        # Create a long conversation
        long_text = "これは長い文章です。" * 100  # 1100 characters
        conversation = Conversation(
            comment=long_text,
            sequence_number=1,
            minutes_id=1,
            speaker_name="山田太郎",
            chapter_number=1,
        )

        # Split with max_length=500
        chunks = service.split_long_conversation(conversation, max_length=500)

        assert len(chunks) > 1
        assert all(len(chunk.comment) <= 500 for chunk in chunks)
        assert all(chunk.speaker_name == "山田太郎" for chunk in chunks)
        assert all(chunk.sequence_number == 1 for chunk in chunks)
        assert chunks[0].sub_chapter_number == 1
        assert chunks[1].sub_chapter_number == 2

        # Verify content is preserved
        combined = "".join(chunk.comment for chunk in chunks)
        assert combined == long_text

    def test_split_long_conversation_short(self, service):
        """Test that short conversations are not split."""
        short_conversation = Conversation(
            comment="これは短い文章です。",
            sequence_number=1,
            minutes_id=1,
            speaker_name="山田太郎",
            chapter_number=1,
        )

        chunks = service.split_long_conversation(short_conversation, max_length=100)

        assert len(chunks) == 1
        assert chunks[0] == short_conversation

    def test_split_into_sentences(self, service):
        """Test splitting text into sentences."""
        # Test with various sentence endings
        text = "これは最初の文です。これは二番目の文！三番目の文？\n四番目の文"
        sentences = service._split_into_sentences(text)

        assert len(sentences) == 5  # Newline is treated as a separate sentence
        assert sentences[0] == "これは最初の文です。"
        assert sentences[1] == "これは二番目の文！"
        assert sentences[2] == "三番目の文？"
        assert sentences[3] == "\n"
        assert sentences[4] == "四番目の文"

        # Test without sentence endings
        text = "句読点のない文章"
        sentences = service._split_into_sentences(text)
        assert len(sentences) == 1
        assert sentences[0] == "句読点のない文章"

    def test_calculate_processing_duration(self, service):
        """Test processing duration calculation."""
        start = datetime(2023, 1, 1, 10, 0, 0, tzinfo=UTC)
        end = datetime(2023, 1, 1, 10, 5, 30, tzinfo=UTC)

        duration = service.calculate_processing_duration(start, end)
        assert duration == 330.0  # 5 minutes 30 seconds

        # Test same time
        duration = service.calculate_processing_duration(start, start)
        assert duration == 0.0

    def test_is_minutes_processed(self, service):
        """Test checking if minutes are processed."""
        # Processed minutes
        processed = Minutes(
            id=1,
            meeting_id=1,
            url="test.pdf",
            processed_at=datetime.now(UTC),
        )
        assert service.is_minutes_processed(processed) is True

        # Unprocessed minutes
        unprocessed = Minutes(
            id=2,
            meeting_id=1,
            url="test.pdf",
            processed_at=None,
        )
        assert service.is_minutes_processed(unprocessed) is False

    def test_validate_conversation_sequence_valid(self, service, sample_conversations):
        """Test validation of valid conversation sequence."""
        issues = service.validate_conversation_sequence(sample_conversations)
        assert len(issues) == 0

    def test_validate_conversation_sequence_invalid(self, service):
        """Test validation of invalid conversation sequences."""
        # No conversations
        issues = service.validate_conversation_sequence([])
        assert "No conversations found" in issues

        # Non-continuous sequence
        conversations = [
            Conversation(
                comment="発言1", sequence_number=1, minutes_id=1, chapter_number=1
            ),
            Conversation(
                comment="発言2", sequence_number=3, minutes_id=1, chapter_number=1
            ),  # Skip 2
            Conversation(
                comment="発言3", sequence_number=4, minutes_id=1, chapter_number=1
            ),
        ]
        issues = service.validate_conversation_sequence(conversations)
        assert "Sequence numbers are not continuous" in issues

        # Empty content
        conversations = [
            Conversation(
                comment="発言1", sequence_number=1, minutes_id=1, chapter_number=1
            ),
            Conversation(
                comment="", sequence_number=2, minutes_id=1, chapter_number=1
            ),  # Empty
            Conversation(
                comment="  ", sequence_number=3, minutes_id=1, chapter_number=1
            ),  # Whitespace
        ]
        issues = service.validate_conversation_sequence(conversations)
        assert "2 conversations have empty content" in issues
