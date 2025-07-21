"""Tests for SpeakerRepository.get_all_speakers_with_conversation_count."""

from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from src.database.speaker_repository import SpeakerRepository


class MockResult:
    """Mock result object."""

    def __init__(self, **kwargs: Any) -> None:
        for key, value in kwargs.items():
            setattr(self, key, value)


@pytest.fixture
def speaker_repo():
    """Create a SpeakerRepository instance."""
    return SpeakerRepository()


def test_get_all_speakers_with_conversation_count_empty(
    speaker_repo: SpeakerRepository,
) -> None:
    """Test getting speakers with conversation count when no data exists."""
    # Mock execute_query for count and main query
    with patch.object(speaker_repo, "execute_query") as mock_execute_query:
        # Mock count query result
        count_result = MagicMock()
        count_result.fetchone.return_value = (0,)

        # Mock main query result
        main_result = MagicMock()
        main_result.keys.return_value = [
            "id",
            "name",
            "type",
            "political_party_name",
            "position",
            "is_politician",
            "conversation_count",
        ]
        main_result.fetchall.return_value = []

        mock_execute_query.side_effect = [count_result, main_result]

        # Act
        result, total = speaker_repo.get_all_speakers_with_conversation_count()

        # Assert
        assert result == []
        assert total == 0

        # Verify queries
        assert mock_execute_query.call_count == 2


def test_get_all_speakers_with_conversation_count_with_data(
    speaker_repo: SpeakerRepository,
) -> None:
    """Test getting speakers with conversation count with data."""
    # Mock execute_query for count and main query
    with patch.object(speaker_repo, "execute_query") as mock_execute_query:
        # Mock count query result
        count_result = MagicMock()
        count_result.fetchone.return_value = (2,)

        # Mock main query result
        main_result = MagicMock()
        main_result.keys.return_value = [
            "id",
            "name",
            "type",
            "political_party_name",
            "position",
            "is_politician",
            "conversation_count",
        ]
        main_result.fetchall.return_value = [
            (1, "テスト議員1", "政治家", "テスト党", "議員", True, 5),
            (2, "テスト参考人", "参考人", None, None, False, 0),
        ]

        mock_execute_query.side_effect = [count_result, main_result]

        # Act
        result, total = speaker_repo.get_all_speakers_with_conversation_count()

        # Assert
        assert len(result) == 2
        assert total == 2

        # Check first speaker
        assert result[0]["id"] == 1
        assert result[0]["name"] == "テスト議員1"
        assert result[0]["type"] == "政治家"
        assert result[0]["political_party_name"] == "テスト党"
        assert result[0]["position"] == "議員"
        assert result[0]["is_politician"] is True
        assert result[0]["conversation_count"] == 5

        # Check second speaker
        assert result[1]["id"] == 2
        assert result[1]["name"] == "テスト参考人"
        assert result[1]["type"] == "参考人"
        assert result[1]["political_party_name"] is None
        assert result[1]["position"] is None
        assert result[1]["is_politician"] is False
        assert result[1]["conversation_count"] == 0


def test_get_all_speakers_with_conversation_count_with_pagination(
    speaker_repo: SpeakerRepository,
) -> None:
    """Test pagination in get_all_speakers_with_conversation_count."""
    # Mock execute_query for count and main query
    with patch.object(speaker_repo, "execute_query") as mock_execute_query:
        # Mock count query result
        count_result = MagicMock()
        count_result.fetchone.return_value = (100,)

        # Mock main query result - only 20 items for limit
        main_result = MagicMock()
        main_result.keys.return_value = [
            "id",
            "name",
            "type",
            "political_party_name",
            "position",
            "is_politician",
            "conversation_count",
        ]
        main_result.fetchall.return_value = [
            (i, f"テスト議員{i}", "政治家", "テスト党", "議員", True, i * 2)
            for i in range(21, 41)  # Second page data
        ]

        mock_execute_query.side_effect = [count_result, main_result]

        # Act - request second page
        result, total = speaker_repo.get_all_speakers_with_conversation_count(
            offset=20, limit=20
        )

        # Assert
        assert len(result) == 20
        assert total == 100
        assert result[0]["id"] == 21  # First item of second page

        # Verify pagination parameters
        assert mock_execute_query.call_count == 2
        # Check the second call (main query) has correct params
        call_args = mock_execute_query.call_args_list[1]
        assert call_args[0][1]["limit"] == 20
        assert call_args[0][1]["offset"] == 20


def test_get_all_speakers_with_conversation_count_no_total(
    speaker_repo: SpeakerRepository,
) -> None:
    """Test handling when total count query returns None."""
    # Mock execute_query for count and main query
    with patch.object(speaker_repo, "execute_query") as mock_execute_query:
        # Mock count query result - returns None
        count_result = MagicMock()
        count_result.fetchone.return_value = None

        # Mock main query result
        main_result = MagicMock()
        main_result.keys.return_value = [
            "id",
            "name",
            "type",
            "political_party_name",
            "position",
            "is_politician",
            "conversation_count",
        ]
        main_result.fetchall.return_value = []

        mock_execute_query.side_effect = [count_result, main_result]

        # Act
        result, total = speaker_repo.get_all_speakers_with_conversation_count()

        # Assert
        assert result == []
        assert total == 0
