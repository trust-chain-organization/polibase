"""Shared pytest fixtures."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from tests.fixtures.dto_factories import (
    create_extracted_speech_dto,
    create_politician_dto,
    create_process_minutes_dto,
    create_speaker_dto,
)
from tests.fixtures.entity_factories import (
    create_conference,
    create_conversation,
    create_governing_body,
    create_meeting,
    create_minutes,
    create_parliamentary_group,
    create_political_party,
    create_politician,
    create_speaker,
)


# Entity fixtures
@pytest.fixture
def sample_governing_body():
    """Create a sample governing body."""
    return create_governing_body()


@pytest.fixture
def sample_conference():
    """Create a sample conference."""
    return create_conference()


@pytest.fixture
def sample_meeting():
    """Create a sample meeting."""
    return create_meeting()


@pytest.fixture
def sample_minutes():
    """Create a sample minutes."""
    return create_minutes()


@pytest.fixture
def sample_speaker():
    """Create a sample speaker."""
    return create_speaker()


@pytest.fixture
def sample_politician():
    """Create a sample politician."""
    return create_politician()


@pytest.fixture
def sample_political_party():
    """Create a sample political party."""
    return create_political_party()


@pytest.fixture
def sample_conversation():
    """Create a sample conversation."""
    return create_conversation()


@pytest.fixture
def sample_parliamentary_group():
    """Create a sample parliamentary group."""
    return create_parliamentary_group()


# DTO fixtures
@pytest.fixture
def sample_process_minutes_dto():
    """Create a sample ProcessMinutesDTO."""
    return create_process_minutes_dto()


@pytest.fixture
def sample_extracted_speech_dto():
    """Create a sample ExtractedSpeechDTO."""
    return create_extracted_speech_dto()


@pytest.fixture
def sample_speaker_dto():
    """Create a sample SpeakerDTO."""
    return create_speaker_dto()


@pytest.fixture
def sample_politician_dto():
    """Create a sample PoliticianDTO."""
    return create_politician_dto()


# Mock repository fixtures
@pytest.fixture
def mock_base_repository():
    """Create a mock base repository."""
    repo = AsyncMock()
    repo.get_by_id.return_value = None
    repo.get_all.return_value = []
    repo.create.return_value = None
    repo.update.return_value = None
    repo.delete.return_value = True
    return repo


@pytest.fixture
def mock_speaker_repository(mock_base_repository):
    """Create a mock speaker repository."""
    repo = mock_base_repository
    repo.get_by_name_party_position.return_value = None
    repo.get_politicians.return_value = []
    repo.upsert.return_value = create_speaker()
    return repo


@pytest.fixture
def mock_politician_repository(mock_base_repository):
    """Create a mock politician repository."""
    repo = mock_base_repository
    repo.get_by_speaker_id.return_value = None
    repo.get_by_name_and_party.return_value = None
    repo.get_by_party.return_value = []
    repo.search_by_name.return_value = []
    return repo


@pytest.fixture
def mock_meeting_repository(mock_base_repository):
    """Create a mock meeting repository."""
    repo = mock_base_repository
    repo.get_by_conference.return_value = []
    repo.get_recent.return_value = []
    return repo


@pytest.fixture
def mock_minutes_repository(mock_base_repository):
    """Create a mock minutes repository."""
    repo = mock_base_repository
    repo.get_by_meeting.return_value = None
    repo.mark_processed.return_value = None
    return repo


@pytest.fixture
def mock_conversation_repository(mock_base_repository):
    """Create a mock conversation repository."""
    repo = mock_base_repository
    repo.bulk_create.return_value = []
    repo.get_by_minutes.return_value = []
    repo.update_speaker_links.return_value = 0
    return repo


# Mock service fixtures
@pytest.fixture
def mock_speaker_domain_service():
    """Create a mock speaker domain service."""
    service = MagicMock()
    service.normalize_speaker_name.side_effect = lambda x: x.strip()
    service.extract_party_from_name.return_value = ("山田太郎", None)
    service.calculate_name_similarity.return_value = 0.9
    service.is_likely_politician.return_value = True
    return service


@pytest.fixture
def mock_politician_domain_service():
    """Create a mock politician domain service."""
    service = MagicMock()
    service.normalize_politician_name.side_effect = lambda x: x.strip()
    service.is_duplicate_politician.return_value = None
    service.merge_politician_info.side_effect = lambda x, y: x
    service.validate_politician_data.return_value = []
    return service


@pytest.fixture
def mock_minutes_domain_service():
    """Create a mock minutes domain service."""
    service = MagicMock()
    service.is_minutes_processed.return_value = False
    service.calculate_processing_duration.return_value = 10.0
    service.create_conversations_from_speeches.return_value = []
    service.validate_conversation_sequence.return_value = []
    return service


@pytest.fixture
def mock_llm_service():
    """Create a mock LLM service."""
    service = AsyncMock()
    service.match_speaker_to_politician.return_value = {"politician_id": None}
    service.extract_conference_members.return_value = []
    service.scrape_party_members.return_value = []
    return service


# Test data fixtures
@pytest.fixture
def current_datetime():
    """Get current datetime with timezone."""
    return datetime.now(UTC)


@pytest.fixture
def test_speeches():
    """Create test speech data."""
    return [
        {"speaker": "山田太郎", "content": "本日の議題について説明します。"},
        {"speaker": "鈴木花子", "content": "質問があります。"},
        {"speaker": "田中次郎", "content": "賛成です。"},
    ]
