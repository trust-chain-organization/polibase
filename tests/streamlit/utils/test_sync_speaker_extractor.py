"""Tests for sync_speaker_extractor module"""

from unittest.mock import Mock, patch

import pytest

from src.domain.entities.conversation import Conversation
from src.domain.entities.speaker import Speaker
from src.streamlit.utils.sync_speaker_extractor import (
    SyncSpeakerExtractionResult,
    SyncSpeakerExtractor,
)


class TestSyncSpeakerExtractor:
    """Test cases for SyncSpeakerExtractor"""

    def test_extract_and_create_speakers_with_conversation_update(self):
        """Test that _extract_and_create_speakers updates conversation speaker_ids"""
        # Arrange
        meeting_id = 1
        extractor = SyncSpeakerExtractor(meeting_id)

        # Mock conversations
        conv1 = Mock(spec=Conversation)
        conv1.id = 1
        conv1.speaker_name = "山田太郎"
        conv1.speaker_id = None

        conv2 = Mock(spec=Conversation)
        conv2.id = 2
        conv2.speaker_name = "議長"  # Role that will be resolved
        conv2.speaker_id = None

        conv3 = Mock(spec=Conversation)
        conv3.id = 3
        conv3.speaker_name = "(「異議なし」と呼ぶ者あり)"  # Non-person
        conv3.speaker_id = None

        conversations = [conv1, conv2, conv3]

        # Mock speaker repo
        speaker_repo = Mock()
        created_speaker = Mock(spec=Speaker)
        created_speaker.id = 101
        created_speaker.name = "山田太郎"
        speaker_repo.create.return_value = created_speaker
        speaker_repo.get_by_name_party_position.return_value = (
            None  # No existing speakers
        )

        # Mock speaker service
        speaker_service = Mock()
        speaker_service.is_non_person_speaker.side_effect = (
            lambda x: x == "(「異議なし」と呼ぶ者あり)"
        )
        speaker_service.resolve_speaker_with_attendees.side_effect = lambda x, _: (
            "西村義直" if x == "議長" else x
        )
        speaker_service.extract_party_from_name.side_effect = lambda x: (x, None)

        # Mock meeting repo for attendees mapping
        with patch("src.config.database.get_db_session_context"):
            with patch(
                "src.streamlit.utils.sync_speaker_extractor.RepositoryAdapter"
            ) as mock_repo_adapter:
                # Mock for meeting repo
                meeting_repo_mock = Mock()
                meeting = Mock()
                meeting.attendees_mapping = {
                    "regular_attendees": ["西村義直", "山田太郎"]
                }
                meeting_repo_mock.get_by_id.return_value = meeting

                # Mock for conversation repo
                conversation_repo_mock = Mock()

                def repo_adapter_side_effect(repo_class, *args):
                    if "MeetingRepositoryImpl" in str(repo_class):
                        return meeting_repo_mock
                    elif "ConversationRepositoryImpl" in str(repo_class):
                        return conversation_repo_mock
                    return Mock()

                mock_repo_adapter.side_effect = repo_adapter_side_effect

                # Act
                result = extractor._extract_and_create_speakers(
                    conversations, speaker_repo, speaker_service
                )

                # Assert
                # Check that conversations were updated with speaker_ids
                assert conv1.speaker_id == 101  # 山田太郎's speaker ID
                assert conv2.speaker_id is not None  # 議長 resolved to 西村義直
                assert conv3.speaker_id is None  # Non-person should not get speaker_id

                # Check that conversation repo update was called
                assert conversation_repo_mock.update.call_count >= 1

                # Check result statistics
                assert result["unique_speakers"] == 2  # 山田太郎 and 西村義直
                assert "role_conversions" in result
                assert ("議長", "西村義直") in result["role_conversions"]

    def test_process_with_existing_speakers(self):
        """Test process method when speakers already exist with conversations linked"""
        # Arrange
        meeting_id = 1
        extractor = SyncSpeakerExtractor(meeting_id)

        # Mock repositories
        with patch(
            "src.streamlit.utils.sync_speaker_extractor.RepositoryAdapter"
        ) as mock_repo_adapter:
            minutes_repo = Mock()
            minutes = Mock()
            minutes.id = 1
            minutes_repo.get_by_meeting.return_value = minutes

            conversation_repo = Mock()
            # Create conversations with some already having speaker_ids
            conv_with_speaker = Mock()
            conv_with_speaker.speaker_id = 100  # Already has speaker
            conversation_repo.get_by_minutes.return_value = [conv_with_speaker]

            speaker_repo = Mock()

            def repo_adapter_side_effect(repo_class):
                class_name = str(repo_class)
                if "MinutesRepositoryImpl" in class_name:
                    return minutes_repo
                elif "ConversationRepositoryImpl" in class_name:
                    return conversation_repo
                elif "SpeakerRepositoryImpl" in class_name:
                    return speaker_repo
                return Mock()

            mock_repo_adapter.side_effect = repo_adapter_side_effect

            # Act & Assert
            with pytest.raises(
                ValueError,
                match="Meeting 1 already has 1 conversations with speakers linked",
            ):
                extractor.process()

    def test_process_success_with_attendees_extraction(self):
        """Test successful processing with attendees extraction"""
        # Arrange
        meeting_id = 1
        extractor = SyncSpeakerExtractor(meeting_id)

        with patch(
            "src.streamlit.utils.sync_speaker_extractor.RepositoryAdapter"
        ) as mock_repo_adapter:
            # Setup all the mocks
            minutes_repo = Mock()
            minutes = Mock()
            minutes.id = 1
            minutes_repo.get_by_meeting.return_value = minutes

            conversation_repo = Mock()
            conv = Mock()
            conv.id = 1
            conv.speaker_name = "田中一郎"
            conv.speaker_id = None
            conversation_repo.get_by_minutes.return_value = [conv]

            speaker_repo = Mock()
            new_speaker = Mock()
            new_speaker.id = 200
            speaker_repo.create.return_value = new_speaker
            speaker_repo.get_by_name_party_position.return_value = None

            def repo_adapter_side_effect(repo_class):
                class_name = str(repo_class)
                if "MinutesRepositoryImpl" in class_name:
                    return minutes_repo
                elif "ConversationRepositoryImpl" in class_name:
                    return conversation_repo
                elif "SpeakerRepositoryImpl" in class_name:
                    return speaker_repo
                return Mock()

            mock_repo_adapter.side_effect = repo_adapter_side_effect

            # Mock attendees extraction
            with patch.object(
                extractor,
                "_extract_and_save_attendees_mapping",
                return_value={"regular_attendees": ["田中一郎", "山田太郎"]},
            ):
                # Mock speaker service
                with patch(
                    "src.streamlit.utils.sync_speaker_extractor.SpeakerDomainService"
                ) as mock_service_class:
                    speaker_service = Mock()
                    speaker_service.is_non_person_speaker.return_value = False
                    speaker_service.resolve_speaker_with_attendees.side_effect = (
                        lambda x, _: x
                    )
                    speaker_service.extract_party_from_name.return_value = (
                        "田中一郎",
                        None,
                    )
                    mock_service_class.return_value = speaker_service

                    # Act
                    result = extractor.process()

                    # Assert
                    assert isinstance(result, SyncSpeakerExtractionResult)
                    assert result.meeting_id == meeting_id
                    assert result.total_conversations == 1
                    assert result.unique_speakers == 1
                    assert result.new_speakers == 1
                    assert result.existing_speakers == 0
                    assert result.errors is None
