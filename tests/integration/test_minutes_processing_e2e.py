"""End-to-end test for minutes processing with history recording."""

import os
from unittest.mock import Mock, patch

from src.process_minutes import main, process_minutes


class TestMinutesProcessingE2E:
    """End-to-end tests for minutes processing with history recording."""

    @patch("src.process_minutes.LLMServiceFactory")
    @patch.dict(os.environ, {"GOOGLE_API_KEY": "test-key"})
    def test_process_minutes_with_mocked_llm_service(self, mock_factory_class):
        """Test process_minutes with mocked LLM service."""
        # Import required models
        from src.minutes_divide_processor.models import SpeakerAndSpeechContent

        # Short test text to minimize API usage
        test_text = """
        第1回定例会議事録

        開会の辞
        議長: 本日の会議を開催します。

        議事
        田中委員: 予算について質問があります。
        山田委員: 私も同意見です。

        閉会
        議長: 以上で本日の会議を終了します。
        """

        # Mock the LLM service factory
        mock_factory = Mock()
        mock_llm_service = Mock()

        # Configure mocks for MinutesDivider
        mock_llm_service.get_structured_llm = Mock(return_value=lambda x: x)
        mock_llm_service.get_prompt = Mock(return_value=Mock())

        # Mock MinutesProcessAgent to return expected results
        with patch("src.process_minutes.MinutesProcessAgent") as mock_agent_class:
            mock_agent = Mock()
            mock_agent.run.return_value = [
                SpeakerAndSpeechContent(
                    chapter_number=1,
                    sub_chapter_number=1,
                    speech_order=1,
                    speaker="議長",
                    speech_content="本日の会議を開催します。",
                ),
                SpeakerAndSpeechContent(
                    chapter_number=2,
                    sub_chapter_number=1,
                    speech_order=1,
                    speaker="田中委員",
                    speech_content="予算について質問があります。",
                ),
                SpeakerAndSpeechContent(
                    chapter_number=2,
                    sub_chapter_number=1,
                    speech_order=2,
                    speaker="山田委員",
                    speech_content="私も同意見です。",
                ),
                SpeakerAndSpeechContent(
                    chapter_number=3,
                    sub_chapter_number=1,
                    speech_order=1,
                    speaker="議長",
                    speech_content="以上で本日の会議を終了します。",
                ),
            ]
            mock_agent_class.return_value = mock_agent

            mock_factory.create_advanced.return_value = mock_llm_service
            mock_factory_class.return_value = mock_factory

            # Process the text
            results = process_minutes(test_text, meeting_id=999)

            # Verify results
            assert isinstance(results, list)
            assert len(results) == 4

            # Check that conversations were extracted correctly
            assert results[0].speaker == "議長"
            assert results[0].speech_content == "本日の会議を開催します。"
            assert results[1].speaker == "田中委員"
            assert results[1].speech_content == "予算について質問があります。"
            assert results[2].speaker == "山田委員"
            assert results[2].speech_content == "私も同意見です。"
            assert results[3].speaker == "議長"
            assert results[3].speech_content == "以上で本日の会議を終了します。"

            # Verify the agent was called with the text
            mock_agent.run.assert_called_once_with(original_minutes=test_text)

    @patch("sys.argv", ["process_minutes.py"])
    @patch("src.process_minutes.load_pdf_text")
    @patch("src.process_minutes.save_to_database")
    @patch("src.process_minutes.display_database_status")
    @patch("src.process_minutes.LLMServiceFactory")
    def test_main_function_with_mocked_dependencies(
        self,
        mock_factory_class,
        mock_display_status,
        mock_save_to_db,
        mock_load_pdf,
    ):
        """Test main function with mocked dependencies."""
        # Mock PDF text
        mock_load_pdf.return_value = "テスト議事録"

        # Mock database save
        mock_save_to_db.return_value = [1, 2, 3]

        # Mock LLM service factory
        mock_factory = Mock()
        mock_llm_service = Mock()

        # Configure mocks for MinutesDivider
        mock_llm_service.get_structured_llm = Mock(return_value=lambda x: x)
        mock_llm_service.get_prompt = Mock(return_value=Mock())

        # Import models for proper return type
        from src.minutes_divide_processor.models import (
            SectionInfo,
            SectionInfoList,
            SpeakerAndSpeechContent,
        )

        mock_llm_service.invoke_with_retry = Mock(
            return_value=SectionInfoList(
                section_info_list=[
                    SectionInfo(chapter_number=1, keyword="開会"),
                ]
            )
        )

        mock_factory.create_advanced.return_value = mock_llm_service
        mock_factory_class.return_value = mock_factory

        # Mock MinutesProcessAgent
        with patch("src.process_minutes.MinutesProcessAgent") as mock_agent_class:
            mock_agent = Mock()
            mock_agent.run.return_value = [
                SpeakerAndSpeechContent(
                    chapter_number=1,
                    speech_order=1,
                    speaker="テスト議員",
                    speech_content="テスト発言",
                )
            ]
            mock_agent_class.return_value = mock_agent

            # Call main
            result = main()

            # Verify
            assert result == [1, 2, 3]
            mock_load_pdf.assert_called_once()
            mock_save_to_db.assert_called_once()
            mock_display_status.assert_called()

    def test_instrumented_service_configuration_in_process_minutes(self):
        """Test that InstrumentedLLMService is properly configured."""
        from src.infrastructure.external.instrumented_llm_service import (
            InstrumentedLLMService,
        )

        with patch("src.process_minutes.LLMServiceFactory") as mock_factory_class:
            # Create a real InstrumentedLLMService mock
            mock_llm = Mock()
            instrumented_service = InstrumentedLLMService(
                llm_service=mock_llm,
                model_name="test-model",
                model_version="1.0",
            )

            # Configure factory to return instrumented service
            mock_factory = Mock()
            mock_factory.create_advanced.return_value = instrumented_service
            mock_factory_class.return_value = mock_factory

            # Mock MinutesProcessAgent
            with patch("src.process_minutes.MinutesProcessAgent") as mock_agent_class:
                mock_agent = Mock()
                mock_agent.run.return_value = []
                mock_agent_class.return_value = mock_agent

                # Call process_minutes with meeting_id
                process_minutes("test", meeting_id=123)

                # Verify that the service was configured with meeting context
                assert instrumented_service._input_reference_type == "meeting"
                assert instrumented_service._input_reference_id == 123
