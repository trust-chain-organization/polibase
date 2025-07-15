"""Test for extract_speakers_from_minutes.py module"""

from unittest.mock import Mock, patch

import pytest
from sqlalchemy.orm import Session

from src.extract_speakers_from_minutes import SpeakerExtractorFromMinutes, main


class TestSpeakerExtractorFromMinutes:
    """Test for SpeakerExtractorFromMinutes class"""

    @pytest.fixture
    def mock_session(self):
        """Create a mock session"""
        session = Mock(spec=Session)
        return session

    @pytest.fixture
    def extractor(self, mock_session):
        """Create SpeakerExtractorFromMinutes instance with mocked repositories"""
        with (
            patch("src.extract_speakers_from_minutes.SpeakerRepository"),
            patch("src.extract_speakers_from_minutes.PoliticianRepository"),
            patch("src.extract_speakers_from_minutes.ConversationRepository"),
            patch("src.extract_speakers_from_minutes.MeetingRepository"),
        ):
            return SpeakerExtractorFromMinutes(mock_session)

    def test_extract_speakers_from_minutes_with_minutes_id(self, extractor):
        """Test extracting speakers from specific minutes"""
        # Arrange
        minutes_id = 123
        mock_conversations = [
            {"id": 1, "speaker_name": "田中太郎", "comment": "質問します"},
            {"id": 2, "speaker_name": "佐藤花子", "comment": "回答します"},
            {
                "id": 3,
                "speaker_name": "田中太郎",
                "comment": "追加質問します",
            },  # Duplicate
        ]

        extractor.conversation_repo.get_conversations_by_minutes_id.return_value = (
            mock_conversations
        )
        extractor.speaker_repo.find_by_name.side_effect = [
            None,  # 田中太郎 not found
            None,  # 佐藤花子 not found
        ]
        # Mock execute_query for insert operations
        mock_result = Mock()
        mock_result.fetchone.side_effect = [(1,), (2,)]  # Return speaker IDs
        extractor.speaker_repo.execute_query.return_value = mock_result

        # Act
        extractor.extract_speakers_from_minutes(minutes_id)

        # Assert
        assert (
            extractor.conversation_repo.get_conversations_by_minutes_id.call_count == 1
        )
        assert (
            extractor.speaker_repo.execute_query.call_count == 2
        )  # Two unique speakers
        extractor.session.commit.assert_called_once()

    def test_extract_speakers_from_minutes_without_minutes_id(self, extractor):
        """Test extracting speakers from all minutes"""
        # Arrange
        mock_conversations = [
            {"id": 1, "speaker_name": "山田太郎", "comment": "発言1"},
            {"id": 2, "speaker_name": "山田太郎", "comment": "発言2"},
        ]

        extractor.conversation_repo.get_all_conversations_without_speaker_id.return_value = mock_conversations  # noqa: E501
        # Mock find_by_name to return existing speaker
        mock_speaker = Mock()
        mock_speaker.id = 10
        extractor.speaker_repo.find_by_name.return_value = mock_speaker

        # Act
        extractor.extract_speakers_from_minutes()

        # Assert
        assert (
            extractor.conversation_repo.get_all_conversations_without_speaker_id.call_count
            == 1
        )
        assert (
            extractor.speaker_repo.execute_query.call_count == 0
        )  # No new speakers created
        extractor.session.commit.assert_called_once()

    def test_extract_speakers_handles_object_conversations(self, extractor):
        """Test handling conversation objects (not dicts)"""
        # Arrange
        mock_conv_obj = Mock()
        mock_conv_obj.speaker_name = "鈴木一郎"

        extractor.conversation_repo.get_all_conversations_without_speaker_id.return_value = [  # noqa: E501
            mock_conv_obj
        ]
        extractor.speaker_repo.find_by_name.return_value = None
        mock_result = Mock()
        mock_result.fetchone.return_value = (3,)
        extractor.speaker_repo.execute_query.return_value = mock_result

        # Act
        extractor.extract_speakers_from_minutes()

        # Assert
        assert extractor.speaker_repo.execute_query.call_count == 1
        query_call = extractor.speaker_repo.execute_query.call_args
        assert query_call[0][1]["name"] == "鈴木一郎"

    def test_extract_speakers_handles_insert_error(self, extractor):
        """Test handling of database insert errors"""
        # Arrange
        mock_conversations = [
            {"id": 1, "speaker_name": "エラー太郎", "comment": "発言"}
        ]

        extractor.conversation_repo.get_all_conversations_without_speaker_id.return_value = mock_conversations  # noqa: E501
        extractor.speaker_repo.fetch_as_dict.return_value = []
        extractor.speaker_repo.insert.side_effect = Exception("DB error")

        # Act
        extractor.extract_speakers_from_minutes()

        # Assert
        # Should still commit other changes
        extractor.session.commit.assert_called_once()

    def test_link_speakers_to_politicians_rule_based(self, extractor):
        """Test rule-based speaker to politician linking"""
        # Arrange
        mock_speakers = [
            {"id": 1, "name": "田中太郎", "political_party_name": None},
            {"id": 2, "name": "佐藤花子", "political_party_name": "自民党"},
        ]
        # Mock execute_query to return speakers
        mock_result = Mock()
        mock_result.fetchall.return_value = [
            (1, "田中太郎", None),
            (2, "佐藤花子", "自民党"),
        ]
        mock_result.keys.return_value = ["id", "name", "political_party_name"]
        extractor.speaker_repo.execute_query.return_value = mock_result

        # Mock politician searches
        extractor.politician_repo.find_by_name.side_effect = [
            [
                {"id": 100, "political_party_name": "自民党"}
            ],  # Single match for 田中太郎
            [  # Multiple matches for 佐藤花子
                {"id": 200, "political_party_name": "自民党"},
                {"id": 201, "political_party_name": "立憲民主党"},
            ],
        ]

        # Act
        extractor.link_speakers_to_politicians(use_llm=False)

        # Assert
        # execute_query calls: 1 for fetching speakers + 2 for updates + 2 for party name queries
        assert extractor.speaker_repo.execute_query.call_count >= 2
        extractor.session.commit.assert_called_once()

    def test_link_speakers_to_politicians_with_llm(self, extractor):
        """Test LLM-based speaker to politician linking"""
        # Arrange
        with patch(
            "src.database.politician_matching_service.PoliticianMatchingService"
        ) as mock_matching_class:
            mock_matching_service = Mock()
            mock_matching_service.batch_link_speakers_to_politicians.return_value = {
                "successfully_matched": 5,
                "failed_matches": 2,
            }
            mock_matching_class.return_value = mock_matching_service

            # Act
            extractor.link_speakers_to_politicians(use_llm=True)

            # Assert
            mock_matching_class.assert_called_once()
            mock_matching_service.batch_link_speakers_to_politicians.assert_called_once()

    def test_update_conversation_speaker_links_simple(self, extractor):
        """Test simple conversation to speaker linking"""
        # Arrange
        mock_conversations = [
            {"id": 1, "speaker_name": "田中太郎"},
            {"id": 2, "speaker_name": "佐藤花子"},
        ]
        extractor.conversation_repo.get_all_conversations_without_speaker_id.return_value = mock_conversations  # noqa: E501

        # Mock execute_query for speaker queries
        def mock_execute_query(query, params):
            mock_result = Mock()
            if "田中太郎" in str(params):
                mock_result.fetchall.return_value = [(10,)]
                mock_result.keys.return_value = ["id"]
            else:
                mock_result.fetchall.return_value = []
                mock_result.keys.return_value = ["id"]
            return mock_result

        extractor.speaker_repo.execute_query.side_effect = mock_execute_query

        # Act
        extractor.update_conversation_speaker_links(use_llm=False)

        # Assert
        assert (
            extractor.conversation_repo.execute_query.call_count == 1
        )  # Only one linked
        extractor.session.commit.assert_called_once()

    def test_update_conversation_speaker_links_with_llm(self, extractor):
        """Test LLM-based conversation to speaker linking"""
        # Arrange
        mock_conversations = [
            {"id": 1, "speaker_name": "田中議員"},
            {"id": 2, "speaker_name": "佐藤委員"},
        ]
        extractor.conversation_repo.get_all_conversations_without_speaker_id.return_value = mock_conversations  # noqa: E501

        with patch(
            "src.extract_speakers_from_minutes.SpeakerMatchingService"
        ) as mock_matching_class:
            mock_match_result = Mock()
            mock_match_result.matched = True
            mock_match_result.speaker_id = 10

            mock_matching_service = Mock()
            mock_matching_service.find_best_match.return_value = mock_match_result
            mock_matching_class.return_value = mock_matching_service

            # Mock execute_query for speaker details
            mock_result = Mock()
            mock_result.fetchall.return_value = [(10, "田中太郎")]
            mock_result.keys.return_value = ["id", "name"]
            extractor.speaker_repo.execute_query.return_value = mock_result

            # Act
            extractor.update_conversation_speaker_links(use_llm=True)

            # Assert
            assert mock_matching_service.find_best_match.call_count == 2
            assert extractor.conversation_repo.execute_query.call_count == 2
            extractor.session.commit.assert_called_once()


class TestMain:
    """Test for main function"""

    @patch("sys.argv", ["extract_speakers_from_minutes.py"])
    @patch("src.extract_speakers_from_minutes.create_engine")
    @patch("src.extract_speakers_from_minutes.sessionmaker")
    @patch("src.extract_speakers_from_minutes.SpeakerExtractorFromMinutes")
    def test_main_default_execution(
        self, mock_extractor_class, mock_sessionmaker, mock_create_engine
    ):
        """Test main function with default arguments"""
        # Arrange
        mock_session = Mock()
        mock_session_local = Mock()
        mock_session_local.__enter__ = Mock(return_value=mock_session)
        mock_session_local.__exit__ = Mock(return_value=None)
        mock_sessionmaker.return_value.return_value = mock_session_local

        mock_extractor = Mock()
        mock_extractor_class.return_value = mock_extractor

        # Act
        main()

        # Assert
        mock_extractor.extract_speakers_from_minutes.assert_called_once_with(None)
        mock_extractor.link_speakers_to_politicians.assert_called_once_with(
            use_llm=False
        )
        mock_extractor.update_conversation_speaker_links.assert_called_once_with(
            use_llm=False
        )

    @patch(
        "sys.argv",
        ["extract_speakers_from_minutes.py", "--minutes-id", "123", "--use-llm"],
    )
    @patch("src.extract_speakers_from_minutes.create_engine")
    @patch("src.extract_speakers_from_minutes.sessionmaker")
    @patch("src.extract_speakers_from_minutes.SpeakerExtractorFromMinutes")
    def test_main_with_minutes_id_and_llm(
        self, mock_extractor_class, mock_sessionmaker, mock_create_engine
    ):
        """Test main function with minutes ID and LLM flag"""
        # Arrange
        mock_session = Mock()
        mock_session_local = Mock()
        mock_session_local.__enter__ = Mock(return_value=mock_session)
        mock_session_local.__exit__ = Mock(return_value=None)
        mock_sessionmaker.return_value.return_value = mock_session_local

        mock_extractor = Mock()
        mock_extractor_class.return_value = mock_extractor

        # Act
        main()

        # Assert
        mock_extractor.extract_speakers_from_minutes.assert_called_once_with(123)
        mock_extractor.link_speakers_to_politicians.assert_called_once_with(
            use_llm=True
        )
        mock_extractor.update_conversation_speaker_links.assert_called_once_with(
            use_llm=True
        )

    @patch(
        "sys.argv",
        [
            "extract_speakers_from_minutes.py",
            "--skip-extraction",
            "--skip-politician-link",
        ],
    )
    @patch("src.extract_speakers_from_minutes.create_engine")
    @patch("src.extract_speakers_from_minutes.sessionmaker")
    @patch("src.extract_speakers_from_minutes.SpeakerExtractorFromMinutes")
    def test_main_with_skip_flags(
        self, mock_extractor_class, mock_sessionmaker, mock_create_engine
    ):
        """Test main function with skip flags"""
        # Arrange
        mock_session = Mock()
        mock_session_local = Mock()
        mock_session_local.__enter__ = Mock(return_value=mock_session)
        mock_session_local.__exit__ = Mock(return_value=None)
        mock_sessionmaker.return_value.return_value = mock_session_local

        mock_extractor = Mock()
        mock_extractor_class.return_value = mock_extractor

        # Act
        main()

        # Assert
        mock_extractor.extract_speakers_from_minutes.assert_not_called()
        mock_extractor.link_speakers_to_politicians.assert_not_called()
        mock_extractor.update_conversation_speaker_links.assert_called_once_with(
            use_llm=False
        )

    @patch("sys.argv", ["extract_speakers_from_minutes.py"])
    @patch("src.extract_speakers_from_minutes.create_engine")
    @patch("src.extract_speakers_from_minutes.sessionmaker")
    @patch("src.extract_speakers_from_minutes.SpeakerExtractorFromMinutes")
    def test_main_handles_exceptions(
        self, mock_extractor_class, mock_sessionmaker, mock_create_engine
    ):
        """Test main function exception handling"""
        # Arrange
        mock_session = Mock()
        mock_session_local = Mock()
        mock_session_local.__enter__ = Mock(return_value=mock_session)
        mock_session_local.__exit__ = Mock(return_value=None)
        mock_sessionmaker.return_value.return_value = mock_session_local

        mock_extractor = Mock()
        mock_extractor.extract_speakers_from_minutes.side_effect = Exception(
            "Test error"
        )
        mock_extractor_class.return_value = mock_extractor

        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            main()

        assert str(exc_info.value) == "Test error"
        mock_session.rollback.assert_called_once()
