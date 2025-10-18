"""Tests for MinutesProcessAgentService."""

from unittest.mock import MagicMock, patch

import pytest

from src.domain.services.interfaces.llm_service import ILLMService
from src.domain.value_objects.speaker_speech import SpeakerSpeech
from src.infrastructure.external.minutes_processing_service import (
    MinutesProcessAgentService,
)
from src.minutes_divide_processor.models import SpeakerAndSpeechContent


class TestMinutesProcessAgentService:
    """Test cases for MinutesProcessAgentService."""

    @pytest.fixture
    def mock_llm_service(self):
        """Create mock LLM service."""
        mock = MagicMock(spec=ILLMService)
        return mock

    @pytest.fixture
    def service(self, mock_llm_service):
        """Create MinutesProcessAgentService instance."""
        return MinutesProcessAgentService(llm_service=mock_llm_service)

    @pytest.mark.asyncio
    async def test_process_minutes_with_valid_speeches(self, service):
        """Test processing with valid speeches."""
        # Setup
        mock_results = [
            SpeakerAndSpeechContent(
                speaker="山田太郎",
                speech_content="これは発言内容です。",
                chapter_number=1,
                sub_chapter_number=1,
                speech_order=1,
            ),
            SpeakerAndSpeechContent(
                speaker="田中花子",
                speech_content="別の発言内容です。",
                chapter_number=2,
                sub_chapter_number=1,
                speech_order=2,
            ),
        ]

        with patch.object(service.agent, "run", return_value=mock_results):
            # Execute
            result = await service.process_minutes("議事録テキスト")

            # Verify
            assert len(result) == 2
            assert all(isinstance(speech, SpeakerSpeech) for speech in result)
            assert result[0].speaker == "山田太郎"
            assert result[0].speech_content == "これは発言内容です。"
            assert result[1].speaker == "田中花子"
            assert result[1].speech_content == "別の発言内容です。"

    @pytest.mark.asyncio
    async def test_process_minutes_filters_empty_content(self, service):
        """Test that speeches with empty content are filtered out."""
        # Setup - mix of valid and invalid speeches
        mock_results = [
            SpeakerAndSpeechContent(
                speaker="山田太郎",
                speech_content="有効な発言",
                chapter_number=1,
                sub_chapter_number=1,
                speech_order=1,
            ),
            SpeakerAndSpeechContent(
                speaker="田中花子",
                speech_content="",  # Empty content - should be filtered
                chapter_number=2,
                sub_chapter_number=1,
                speech_order=2,
            ),
            SpeakerAndSpeechContent(
                speaker="鈴木一郎",
                speech_content="別の有効な発言",
                chapter_number=3,
                sub_chapter_number=1,
                speech_order=3,
            ),
        ]

        with patch.object(service.agent, "run", return_value=mock_results):
            # Execute
            result = await service.process_minutes("議事録テキスト")

            # Verify - only 2 valid speeches should be returned
            assert len(result) == 2
            assert result[0].speaker == "山田太郎"
            assert result[1].speaker == "鈴木一郎"

    @pytest.mark.asyncio
    async def test_process_minutes_filters_whitespace_only_content(self, service):
        """Test that speeches with whitespace-only content are filtered out."""
        # Setup
        mock_results = [
            SpeakerAndSpeechContent(
                speaker="山田太郎",
                speech_content="有効な発言",
                chapter_number=1,
                sub_chapter_number=1,
                speech_order=1,
            ),
            SpeakerAndSpeechContent(
                speaker="田中花子",
                speech_content="   ",  # Whitespace only - should be filtered
                chapter_number=2,
                sub_chapter_number=1,
                speech_order=2,
            ),
        ]

        with patch.object(service.agent, "run", return_value=mock_results):
            # Execute
            result = await service.process_minutes("議事録テキスト")

            # Verify - only 1 valid speech
            assert len(result) == 1
            assert result[0].speaker == "山田太郎"

    @pytest.mark.asyncio
    async def test_process_minutes_filters_empty_speaker(self, service):
        """Test that speeches with empty speaker names are filtered out."""
        # Setup
        mock_results = [
            SpeakerAndSpeechContent(
                speaker="",  # Empty speaker - should be filtered
                speech_content="発言内容",
                chapter_number=1,
                sub_chapter_number=1,
                speech_order=1,
            ),
            SpeakerAndSpeechContent(
                speaker="田中花子",
                speech_content="有効な発言",
                chapter_number=2,
                sub_chapter_number=1,
                speech_order=2,
            ),
        ]

        with patch.object(service.agent, "run", return_value=mock_results):
            # Execute
            result = await service.process_minutes("議事録テキスト")

            # Verify - only 1 valid speech
            assert len(result) == 1
            assert result[0].speaker == "田中花子"

    @pytest.mark.asyncio
    async def test_process_minutes_filters_whitespace_only_speaker(self, service):
        """Test that speeches with whitespace-only speaker names are filtered out."""
        # Setup
        mock_results = [
            SpeakerAndSpeechContent(
                speaker="   ",  # Whitespace only - should be filtered
                speech_content="発言内容",
                chapter_number=1,
                sub_chapter_number=1,
                speech_order=1,
            ),
            SpeakerAndSpeechContent(
                speaker="田中花子",
                speech_content="有効な発言",
                chapter_number=2,
                sub_chapter_number=1,
                speech_order=2,
            ),
        ]

        with patch.object(service.agent, "run", return_value=mock_results):
            # Execute
            result = await service.process_minutes("議事録テキスト")

            # Verify - only 1 valid speech
            assert len(result) == 1
            assert result[0].speaker == "田中花子"

    @pytest.mark.asyncio
    async def test_process_minutes_returns_empty_list_when_all_filtered(self, service):
        """Test that empty list is returned when all speeches are filtered out."""
        # Setup - all invalid speeches
        mock_results = [
            SpeakerAndSpeechContent(
                speaker="",
                speech_content="発言内容",
                chapter_number=1,
                sub_chapter_number=1,
                speech_order=1,
            ),
            SpeakerAndSpeechContent(
                speaker="田中花子",
                speech_content="",
                chapter_number=2,
                sub_chapter_number=1,
                speech_order=2,
            ),
        ]

        with patch.object(service.agent, "run", return_value=mock_results):
            # Execute
            result = await service.process_minutes("議事録テキスト")

            # Verify - empty list
            assert len(result) == 0

    @pytest.mark.asyncio
    async def test_process_minutes_preserves_order(self, service):
        """Test that speech order is preserved after filtering."""
        # Setup
        mock_results = [
            SpeakerAndSpeechContent(
                speaker="山田太郎",
                speech_content="最初の発言",
                chapter_number=1,
                sub_chapter_number=1,
                speech_order=1,
            ),
            SpeakerAndSpeechContent(
                speaker="",  # Will be filtered
                speech_content="発言内容",
                chapter_number=2,
                sub_chapter_number=1,
                speech_order=2,
            ),
            SpeakerAndSpeechContent(
                speaker="田中花子",
                speech_content="2番目の有効な発言",
                chapter_number=3,
                sub_chapter_number=1,
                speech_order=3,
            ),
            SpeakerAndSpeechContent(
                speaker="鈴木一郎",
                speech_content="3番目の有効な発言",
                chapter_number=4,
                sub_chapter_number=1,
                speech_order=4,
            ),
        ]

        with patch.object(service.agent, "run", return_value=mock_results):
            # Execute
            result = await service.process_minutes("議事録テキスト")

            # Verify - order is preserved
            assert len(result) == 3
            assert result[0].speech_order == 1
            assert result[1].speech_order == 3
            assert result[2].speech_order == 4
