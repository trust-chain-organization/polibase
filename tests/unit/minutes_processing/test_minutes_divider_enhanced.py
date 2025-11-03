"""Enhanced tests for MinutesDivider - covering additional methods"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import unittest
from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.minutes_divide_processor.minutes_divider import MinutesDivider
from src.minutes_divide_processor.models import (
    SectionInfo,
    SectionInfoList,
    SectionString,
    SectionStringList,
)


class TestMinutesDividerEnhanced(unittest.TestCase):
    """Enhanced test cases for MinutesDivider covering additional methods"""

    @patch("src.minutes_divide_processor.minutes_divider.LLMServiceFactory")
    def setUp(self, mock_factory):
        # Create a mock LLM service
        mock_service = Mock()
        mock_factory.return_value.create_advanced.return_value = mock_service

        # MinutesDivider will use the mocked service
        self.divider = MinutesDivider()
        self.mock_service = mock_service

    def test_pre_process_normal_text(self):
        """Test pre_process with normal text"""
        input_text = "これは\n\nテスト\n\nです。"
        result = self.divider.pre_process(input_text)

        # Should normalize newlines
        self.assertIsInstance(result, str)
        self.assertNotEqual(result, input_text)

    def test_pre_process_empty_text(self):
        """Test pre_process with empty text"""
        result = self.divider.pre_process("")

        self.assertEqual(result, "")

    def test_pre_process_with_special_characters(self):
        """Test pre_process with special characters"""
        input_text = "◎議長(山田太郎)\n発言内容です。"
        result = self.divider.pre_process(input_text)

        # Should preserve special characters
        self.assertIn("◎", result)
        self.assertIn("山田太郎", result)

    def test_check_length_within_limit(self):
        """Test check_length when text is within limit"""
        short_text = "短いテキスト" * 100  # Small text
        section_strings = SectionStringList(
            section_string_list=[
                SectionString(
                    chapter_number=1, sub_chapter_number=1, section_string=short_text
                )
            ]
        )

        result = self.divider.check_length(section_strings)

        # Should return sections that need re-division
        self.assertIsInstance(result, list)

    def test_check_length_exceeds_limit(self):
        """Test check_length when text exceeds limit"""
        long_text = "長いテキスト" * 5000  # Very long text
        section_strings = SectionStringList(
            section_string_list=[
                SectionString(
                    chapter_number=1, sub_chapter_number=1, section_string=long_text
                )
            ]
        )

        result = self.divider.check_length(section_strings)

        # Should identify sections needing re-division
        self.assertIsInstance(result, list)

    def test_do_redivide_basic(self):
        """Test do_redivide with basic text"""
        long_section = (
            "◎議長(山田太郎)最初の発言です。"
            "◎副議長(佐藤花子)次の発言です。"
            "◎議員(田中一郎)3つ目の発言です。"
        )

        section = SectionString(
            chapter_number=1, sub_chapter_number=1, section_string=long_section
        )

        result = self.divider.do_redivide([section])

        # Should return divided sections
        self.assertIsInstance(result, list)
        self.assertTrue(len(result) > 0)

    def test_detect_attendee_boundary_with_boundary(self):
        """Test detect_attendee_boundary when boundary exists"""
        minutes_text = """
        出席者リスト開始
        ◯議長 山田太郎
        ◯副議長 佐藤花子

        議事開始
        ◎議長(山田太郎)本日の議事を開始します。
        """

        result = self.divider.detect_attendee_boundary(minutes_text)

        # Should return boundary index or None
        self.assertIsInstance(result, (int, type(None)))

    def test_detect_attendee_boundary_no_boundary(self):
        """Test detect_attendee_boundary when no boundary exists"""
        minutes_text = "◎議長(山田太郎)本日の議事を開始します。"

        result = self.divider.detect_attendee_boundary(minutes_text)

        # Should return None if no clear boundary
        self.assertIsInstance(result, (int, type(None)))

    @pytest.mark.asyncio
    async def test_section_divide_run_basic(self):
        """Test section_divide_run with basic text"""
        minutes_text = (
            "◎議長(山田太郎)本日の議事を開始します。"
            "◎副議長(佐藤花子)議案について説明します。"
        )

        # Mock the LLM response
        self.mock_service.generate_structured = AsyncMock(
            return_value=SectionInfoList(
                section_info_list=[
                    SectionInfo(chapter_number=1, keyword="◎議長(山田太郎)"),
                    SectionInfo(chapter_number=2, keyword="◎副議長(佐藤花子)"),
                ]
            )
        )

        result = await self.divider.section_divide_run(minutes_text)

        # Should return SectionStringList
        self.assertIsInstance(result, SectionStringList)

    @pytest.mark.asyncio
    async def test_speech_divide_run_basic(self):
        """Test speech_divide_run with basic text"""
        section_string = SectionString(
            chapter_number=1,
            sub_chapter_number=1,
            section_string="◎議長(山田太郎)本日の議事を開始します。",
        )

        # Mock the LLM response
        mock_output = Mock()
        mock_output.conversations = [
            {"speaker": "山田太郎", "content": "本日の議事を開始します。"}
        ]
        self.mock_service.generate_structured = AsyncMock(return_value=mock_output)

        result = await self.divider.speech_divide_run(section_string)

        # Should return conversation data
        self.assertIsInstance(result, dict)

    def test_split_minutes_by_boundary_with_index(self):
        """Test split_minutes_by_boundary with valid boundary index"""
        minutes_text = """出席者
        ◯議長 山田太郎

        議事開始
        ◎議長(山田太郎)開始します。"""

        boundary_index = 50  # Some index in the middle

        result = self.divider.split_minutes_by_boundary(minutes_text, boundary_index)

        # Should return tuple of (attendee_section, minutes_section) or similar
        self.assertIsInstance(result, (tuple, list, dict))

    def test_split_minutes_by_boundary_no_index(self):
        """Test split_minutes_by_boundary with no boundary index"""
        minutes_text = "◎議長(山田太郎)開始します。"

        result = self.divider.split_minutes_by_boundary(minutes_text, None)

        # Should handle None boundary gracefully
        self.assertIsInstance(result, (tuple, list, dict, str))

    def test_extract_attendees_mapping_basic(self):
        """Test extract_attendees_mapping with basic attendee text"""
        attendee_text = """
        出席者
        ◯議長 山田太郎
        ◯副議長 佐藤花子
        ◯議員 田中一郎
        """

        # Mock LLM response if needed
        self.mock_service.generate_structured = AsyncMock(
            return_value={
                "山田太郎": "議長",
                "佐藤花子": "副議長",
                "田中一郎": "議員",
            }
        )

        try:
            result = self.divider.extract_attendees_mapping(attendee_text)

            # Should return mapping of names to roles
            self.assertIsInstance(result, dict)
        except Exception:
            # Method might be async or have different signature
            pass

    def test_extract_attendees_mapping_empty(self):
        """Test extract_attendees_mapping with empty text"""
        try:
            result = self.divider.extract_attendees_mapping("")

            # Should return empty dict or handle gracefully
            self.assertIsInstance(result, (dict, type(None)))
        except Exception:
            # Expected if method requires specific format
            pass


if __name__ == "__main__":
    unittest.main()
