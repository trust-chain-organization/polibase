"""Tests for sync_speaker_extractor module - with existing speakers"""

from unittest.mock import Mock, patch

from src.domain.entities.conversation import Conversation
from src.domain.entities.speaker import Speaker
from src.streamlit.utils.sync_speaker_extractor import SyncSpeakerExtractor


class TestSyncSpeakerExtractorWithExisting:
    """Test cases for SyncSpeakerExtractor with existing speakers"""

    def test_extract_and_link_existing_speakers(self):
        """Test linking conversations to existing speakers"""
        # Arrange
        meeting_id = 1
        extractor = SyncSpeakerExtractor(meeting_id)

        # Mock conversations
        conv1 = Mock(spec=Conversation)
        conv1.id = 1
        conv1.speaker_name = "田中一郎"
        conv1.speaker_id = None

        conv2 = Mock(spec=Conversation)
        conv2.id = 2
        conv2.speaker_name = "佐藤次郎"
        conv2.speaker_id = None

        conversations = [conv1, conv2]

        # Mock speaker repo - return existing speakers
        speaker_repo = Mock()
        existing_speaker1 = Mock(spec=Speaker)
        existing_speaker1.id = 201
        existing_speaker1.name = "田中一郎"

        existing_speaker2 = Mock(spec=Speaker)
        existing_speaker2.id = 202
        existing_speaker2.name = "佐藤次郎"

        # Configure mock to return existing speakers
        def get_by_name_party_position_side_effect(name, party, position):
            if name == "田中一郎":
                return existing_speaker1
            elif name == "佐藤次郎":
                return existing_speaker2
            return None

        speaker_repo.get_by_name_party_position.side_effect = (
            get_by_name_party_position_side_effect
        )
        speaker_repo.create.return_value = None  # Should not be called

        # Mock speaker service
        speaker_service = Mock()
        speaker_service.is_non_person_speaker.return_value = False
        speaker_service.resolve_speaker_with_attendees.side_effect = lambda x, _: x
        speaker_service.extract_party_from_name.side_effect = lambda x: (x, None)

        # Mock database session context
        with patch("src.config.database.get_db_session_context") as mock_get_session:
            # Mock session for SQL execution
            mock_session = Mock()
            mock_get_session.return_value.__enter__ = Mock(return_value=mock_session)
            mock_get_session.return_value.__exit__ = Mock(return_value=None)

            with patch(
                "src.streamlit.utils.sync_speaker_extractor.RepositoryAdapter"
            ) as mock_repo_adapter:
                # Mock for meeting repo
                meeting_repo_mock = Mock()
                meeting = Mock()
                meeting.attendees_mapping = None  # No attendees mapping
                meeting_repo_mock.get_by_id.return_value = meeting

                def repo_adapter_side_effect(repo_class, *args):
                    if "MeetingRepositoryImpl" in str(repo_class):
                        return meeting_repo_mock
                    return Mock()

                mock_repo_adapter.side_effect = repo_adapter_side_effect

                # Act
                result = extractor._extract_and_create_speakers(
                    conversations, speaker_repo, speaker_service
                )

                # Assert
                # Check that no new speakers were created
                assert speaker_repo.create.called is False

                # Check that SQL update was executed for linking existing speakers
                assert mock_session.execute.called
                assert mock_session.commit.called

                # Verify the SQL was called with correct parameters
                execute_calls = mock_session.execute.call_args_list
                assert len(execute_calls) == 2  # Two conversations to update

                # Check result statistics
                assert result["unique_speakers"] == 2
                assert result["new_speakers"] == 0
                assert result["existing_speakers"] == 2
