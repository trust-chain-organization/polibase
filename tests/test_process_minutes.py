"""Test for process_minutes.py module"""

import os
from unittest.mock import Mock, patch

import pytest

from src.exceptions import (
    APIKeyError,
    DatabaseError,
    PDFProcessingError,
    ProcessingError,
)
from src.minutes_divide_processor.models import SpeakerAndSpeechContent
from src.process_minutes import (
    display_database_status,
    main,
    process_minutes,
    save_to_database,
)


class TestProcessMinutes:
    """Test for process_minutes function"""

    @patch.dict(os.environ, {"GOOGLE_API_KEY": "test-api-key"})
    @patch("src.process_minutes.ChatGoogleGenerativeAI")
    @patch("src.process_minutes.MinutesProcessAgent")
    def test_process_minutes_success(self, mock_agent_class, mock_llm_class):
        """Test successful minutes processing"""
        # Arrange
        test_text = "これは議事録のテキストです。"
        expected_results = [
            SpeakerAndSpeechContent(
                speaker="田中太郎", speech_content="本日の議題について説明します。"
            ),
            SpeakerAndSpeechContent(
                speaker="佐藤花子", speech_content="その提案に賛成です。"
            ),
        ]

        mock_agent = Mock()
        mock_agent.run.return_value = expected_results
        mock_agent_class.return_value = mock_agent

        # Act
        results = process_minutes(test_text)

        # Assert
        assert results == expected_results
        mock_llm_class.assert_called_once_with(model="gemini-2.0-flash", temperature=0)
        mock_agent_class.assert_called_once_with(llm=mock_llm_class.return_value)
        mock_agent.run.assert_called_once_with(original_minutes=test_text)

    def test_process_minutes_empty_text(self):
        """Test processing with empty text"""
        with pytest.raises(ProcessingError) as exc_info:
            process_minutes("")

        assert "No text provided for processing" in str(exc_info.value)
        assert exc_info.value.details["text_length"] == 0

    @patch.dict(os.environ, {}, clear=True)
    def test_process_minutes_no_api_key(self):
        """Test processing without API key"""
        with pytest.raises(APIKeyError) as exc_info:
            process_minutes("Some text")

        assert "GOOGLE_API_KEY not set" in str(exc_info.value)

    @patch.dict(os.environ, {"GOOGLE_API_KEY": "test-api-key"})
    @patch("src.process_minutes.ChatGoogleGenerativeAI")
    @patch("src.process_minutes.MinutesProcessAgent")
    def test_process_minutes_agent_error(self, mock_agent_class, mock_llm_class):
        """Test handling of agent processing error"""
        # Arrange
        mock_agent = Mock()
        mock_agent.run.side_effect = Exception("Agent processing failed")
        mock_agent_class.return_value = mock_agent

        # Act & Assert
        with pytest.raises(ProcessingError) as exc_info:
            process_minutes("Test text")

        assert "Failed to process meeting minutes" in str(exc_info.value)
        assert "Agent processing failed" in str(exc_info.value.details["error"])


class TestSaveToDatabase:
    """Test for save_to_database function"""

    @patch("src.process_minutes.ConversationRepository")
    def test_save_to_database_success(self, mock_repo_class):
        """Test successful database save"""
        # Arrange
        test_data = [
            SpeakerAndSpeechContent(speaker="山田", speech_content="質問があります"),
            SpeakerAndSpeechContent(speaker="田中", speech_content="回答します"),
        ]
        expected_ids = [101, 102]
        minutes_id = 1

        mock_repo = Mock()
        mock_repo.save_speaker_and_speech_content_list.return_value = expected_ids
        mock_repo_class.return_value = mock_repo

        # Act
        result = save_to_database(test_data, minutes_id=minutes_id)

        # Assert
        assert result == expected_ids
        mock_repo.save_speaker_and_speech_content_list.assert_called_once_with(
            test_data, minutes_id=minutes_id
        )
        mock_repo.close.assert_called_once()

    def test_save_to_database_empty_list(self):
        """Test saving empty list"""
        result = save_to_database([])
        assert result == []

    @patch("src.process_minutes.ConversationRepository")
    def test_save_to_database_error(self, mock_repo_class):
        """Test database save error handling"""
        # Arrange
        test_data = [SpeakerAndSpeechContent(speaker="山田", speech_content="発言")]
        mock_repo = Mock()
        mock_repo.save_speaker_and_speech_content_list.side_effect = Exception(
            "DB error"
        )
        mock_repo_class.return_value = mock_repo

        # Act & Assert
        with pytest.raises(DatabaseError) as exc_info:
            save_to_database(test_data)

        assert "Failed to save conversations to database" in str(exc_info.value)
        mock_repo.close.assert_called_once()  # Ensure cleanup happens


class TestDisplayDatabaseStatus:
    """Test for display_database_status function"""

    @patch("src.process_minutes.ConversationRepository")
    @patch("builtins.print")
    def test_display_database_status_success(self, mock_print, mock_repo_class):
        """Test successful database status display"""
        # Arrange
        mock_repo = Mock()
        mock_repo.get_conversations_count.return_value = 10
        mock_repo.get_speaker_linking_stats.return_value = {
            "linked_conversations": 7,
            "unlinked_conversations": 3,
        }
        mock_repo.get_all_conversations.return_value = [
            {
                "id": 1,
                "speaker_name": "田中",
                "linked_speaker_name": "田中太郎",
                "comment": "本日の議題について説明します。",
            },
            {
                "id": 2,
                "speaker_name": "佐藤",
                "linked_speaker_name": None,
                "comment": "質問があります。",
            },
        ]
        mock_repo_class.return_value = mock_repo

        # Act
        display_database_status()

        # Assert
        mock_repo.get_conversations_count.assert_called_once()
        mock_repo.get_speaker_linking_stats.assert_called_once()
        mock_repo.get_all_conversations.assert_called_once()
        mock_repo.close.assert_called_once()

        # Verify print calls
        print_calls = [call[0][0] for call in mock_print.call_args_list]
        assert any(
            "現在のConversationsテーブルレコード数: 10件" in call
            for call in print_calls
        )
        assert any("Speaker紐付けあり: 7件" in call for call in print_calls)
        assert any("Speaker紐付けなし: 3件" in call for call in print_calls)

    @patch("src.process_minutes.ConversationRepository")
    def test_display_database_status_error(self, mock_repo_class):
        """Test database status display error handling"""
        # Arrange
        mock_repo = Mock()
        mock_repo.get_conversations_count.side_effect = Exception("DB connection error")
        mock_repo_class.return_value = mock_repo

        # Act & Assert
        with pytest.raises(DatabaseError) as exc_info:
            display_database_status()

        assert "Failed to retrieve database status" in str(exc_info.value)
        mock_repo.close.assert_called_once()


class TestMain:
    """Test for main function"""

    @patch("sys.argv", ["process_minutes.py"])
    @patch("src.process_minutes.setup_environment")
    @patch("src.process_minutes.load_pdf_text")
    @patch("src.process_minutes.run_main_process")
    def test_main_default_pdf_processing(
        self, mock_run_main, mock_load_pdf, mock_setup, capsys
    ):
        """Test main function with default PDF processing"""
        # Arrange
        mock_load_pdf.return_value = "PDF content"
        mock_run_main.return_value = [1, 2, 3]

        # Act
        result = main()

        # Assert
        assert result == [1, 2, 3]
        mock_setup.assert_called_once()
        mock_load_pdf.assert_called_once()
        mock_run_main.assert_called_once()

    @patch(
        "sys.argv",
        ["process_minutes.py", "--meeting-id", "123"],
    )
    @patch("src.process_minutes.setup_environment")
    @patch("src.database.meeting_repository.MeetingRepository")
    @patch("src.process_minutes.config")
    @patch("src.utils.gcs_storage.GCSStorage")
    @patch("src.database.base_repository.BaseRepository")
    @patch("src.process_minutes.run_main_process")
    def test_main_with_gcs_meeting_id(
        self,
        mock_run_main,
        mock_base_repo_class,
        mock_gcs_class,
        mock_config,
        mock_meeting_repo_class,
        mock_setup,
    ):
        """Test main function with meeting ID and GCS integration"""
        # Arrange
        mock_meeting_repo = Mock()
        mock_meeting_repo.get_meeting_by_id.return_value = {
            "id": 123,
            "url": "http://example.com",
            "gcs_text_uri": "gs://bucket/file.txt",
        }
        mock_meeting_repo_class.return_value = mock_meeting_repo

        mock_gcs = Mock()
        mock_gcs.download_content.return_value = "GCS content"
        mock_gcs_class.return_value = mock_gcs

        # Mock config values
        mock_config.GCS_BUCKET_NAME = "test-bucket"
        mock_config.GCS_PROJECT_ID = "test-project"

        mock_base_repo = Mock()
        mock_base_repo.fetch_one.return_value = None  # No existing minutes
        mock_base_repo.insert.return_value = 456  # New minutes ID
        mock_base_repo_class.return_value = mock_base_repo

        mock_run_main.return_value = [789]

        # Act
        result = main()

        # Assert
        assert result == [789]
        mock_meeting_repo.get_meeting_by_id.assert_called_once_with(123)
        mock_gcs.download_content.assert_called_once_with("gs://bucket/file.txt")
        mock_base_repo.insert.assert_called_once()

    @patch("sys.argv", ["process_minutes.py", "--process-all-gcs"])
    @patch("src.process_minutes.setup_environment")
    @patch("src.database.meeting_repository.MeetingRepository")
    @patch("src.process_minutes.config")
    @patch("src.utils.gcs_storage.GCSStorage")
    @patch("src.database.base_repository.BaseRepository")
    @patch("src.process_minutes.process_minutes")
    @patch("src.process_minutes.save_to_database")
    @patch("src.process_minutes.display_database_status")
    @patch("builtins.print")
    def test_main_process_all_gcs(
        self,
        mock_print,
        mock_display_status,
        mock_save_db,
        mock_process,
        mock_base_repo_class,
        mock_gcs_class,
        mock_config,
        mock_meeting_repo_class,
        mock_setup,
    ):
        """Test main function with --process-all-gcs flag"""
        # Arrange
        mock_meeting_repo = Mock()
        mock_meeting_repo.fetch_as_dict.return_value = [
            {
                "id": 1,
                "url": "http://example1.com",
                "gcs_text_uri": "gs://bucket/file1.txt",
            },
            {
                "id": 2,
                "url": "http://example2.com",
                "gcs_text_uri": "gs://bucket/file2.txt",
            },
        ]
        mock_meeting_repo_class.return_value = mock_meeting_repo

        mock_gcs = Mock()
        mock_gcs.download_content.side_effect = ["Content 1", "Content 2"]
        mock_gcs_class.return_value = mock_gcs

        # Mock config values
        mock_config.GCS_BUCKET_NAME = "test-bucket"
        mock_config.GCS_PROJECT_ID = "test-project"

        mock_base_repo = Mock()
        mock_base_repo.fetch_one.return_value = None  # No existing minutes
        mock_base_repo.insert.side_effect = [10, 20]  # Minutes IDs
        mock_base_repo_class.return_value = mock_base_repo

        mock_process.side_effect = [
            [SpeakerAndSpeechContent(speaker="A", speech_content="Text1")],
            [SpeakerAndSpeechContent(speaker="B", speech_content="Text2")],
        ]
        mock_save_db.side_effect = [[100], [200]]

        # Act
        result = main()

        # Assert
        assert result == [100, 200]
        assert mock_gcs.download_content.call_count == 2
        assert mock_process.call_count == 2
        assert mock_save_db.call_count == 2
        mock_display_status.assert_called_once()

    @patch("sys.argv", ["process_minutes.py"])
    @patch("src.process_minutes.setup_environment")
    @patch("src.process_minutes.load_pdf_text")
    def test_main_api_key_error(self, mock_load_pdf, mock_setup):
        """Test main function handling API key error"""
        # Arrange
        mock_load_pdf.side_effect = APIKeyError(
            "API key not set", {"env_var": "GOOGLE_API_KEY"}
        )

        # Act & Assert
        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 1

    @patch("sys.argv", ["process_minutes.py"])
    @patch("src.process_minutes.setup_environment")
    @patch("src.process_minutes.load_pdf_text")
    def test_main_pdf_processing_error(self, mock_load_pdf, mock_setup):
        """Test main function handling PDF processing error"""
        # Arrange
        mock_load_pdf.side_effect = PDFProcessingError(
            "Failed to read PDF", {"file": "test.pdf"}
        )

        # Act & Assert
        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 1

    @patch("sys.argv", ["process_minutes.py"])
    @patch("src.process_minutes.setup_environment")
    @patch("src.process_minutes.load_pdf_text")
    @patch("src.process_minutes.run_main_process")
    def test_main_database_error(self, mock_run_main, mock_load_pdf, mock_setup):
        """Test main function handling database error"""
        # Arrange
        mock_load_pdf.return_value = "PDF content"
        mock_run_main.side_effect = DatabaseError(
            "Database connection failed", {"host": "localhost"}
        )

        # Act & Assert
        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 1

    @patch("sys.argv", ["process_minutes.py"])
    @patch("src.process_minutes.setup_environment")
    @patch("src.process_minutes.load_pdf_text")
    def test_main_unexpected_error(self, mock_load_pdf, mock_setup):
        """Test main function handling unexpected error"""
        # Arrange
        mock_load_pdf.side_effect = RuntimeError("Unexpected error occurred")

        # Act & Assert
        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 1
