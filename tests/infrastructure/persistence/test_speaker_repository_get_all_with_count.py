"""Tests for SpeakerRepositoryImpl.get_all_with_conversation_count."""

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.persistence.speaker_repository_impl import SpeakerRepositoryImpl


class MockRow:
    """Mock database row result."""

    def __init__(self, **kwargs: Any) -> None:
        for key, value in kwargs.items():
            setattr(self, key, value)


@pytest.mark.asyncio
async def test_get_all_with_conversation_count_empty():
    """Test getting speakers with conversation count when no data exists."""
    # Arrange
    mock_session = AsyncMock(spec=AsyncSession)
    mock_model = MagicMock()

    # Mock count query result
    count_result = MagicMock()
    count_result.scalar.return_value = 0

    # Mock main query result
    main_result = MagicMock()
    main_result.__iter__ = lambda self: iter([])

    mock_session.execute = AsyncMock(side_effect=[count_result, main_result])

    repo = SpeakerRepositoryImpl(mock_session, mock_model)

    # Act
    result, total = await repo.get_all_with_conversation_count()

    # Assert
    assert result == []
    assert total == 0
    assert mock_session.execute.call_count == 2


@pytest.mark.asyncio
async def test_get_all_with_conversation_count_with_data():
    """Test getting speakers with conversation count with data."""
    # Arrange
    mock_session = AsyncMock(spec=AsyncSession)
    mock_model = MagicMock()

    # Mock count query result
    count_result = MagicMock()
    count_result.scalar.return_value = 2

    # Mock main query result
    mock_rows = [
        MockRow(
            id=1,
            name="テスト議員1",
            type="政治家",
            political_party_name="テスト党",
            position="議員",
            is_politician=True,
            conversation_count=5,
        ),
        MockRow(
            id=2,
            name="テスト参考人",
            type="参考人",
            political_party_name=None,
            position=None,
            is_politician=False,
            conversation_count=0,
        ),
    ]

    main_result = MagicMock()
    main_result.__iter__ = lambda self: iter(mock_rows)

    mock_session.execute = AsyncMock(side_effect=[count_result, main_result])

    repo = SpeakerRepositoryImpl(mock_session, mock_model)

    # Act
    result, total = await repo.get_all_with_conversation_count(offset=0, limit=10)

    # Assert
    assert len(result) == 2
    assert total == 2

    # Check first speaker
    speaker1, count1 = result[0]
    assert speaker1.id == 1
    assert speaker1.name == "テスト議員1"
    assert speaker1.type == "政治家"
    assert speaker1.political_party_name == "テスト党"
    assert speaker1.position == "議員"
    assert speaker1.is_politician is True
    assert count1 == 5

    # Check second speaker
    speaker2, count2 = result[1]
    assert speaker2.id == 2
    assert speaker2.name == "テスト参考人"
    assert speaker2.type == "参考人"
    assert speaker2.political_party_name is None
    assert speaker2.position is None
    assert speaker2.is_politician is False
    assert count2 == 0


@pytest.mark.asyncio
async def test_get_all_with_conversation_count_with_pagination():
    """Test pagination in get_all_with_conversation_count."""
    # Arrange
    mock_session = AsyncMock(spec=AsyncSession)
    mock_model = MagicMock()

    # Mock count query result
    count_result = MagicMock()
    count_result.scalar.return_value = 100

    # Mock main query result - only 20 items for limit
    mock_rows = [
        MockRow(
            id=i,
            name=f"テスト議員{i}",
            type="政治家",
            political_party_name="テスト党",
            position="議員",
            is_politician=True,
            conversation_count=i * 2,
        )
        for i in range(1, 21)
    ]

    main_result = MagicMock()
    main_result.__iter__ = lambda self: iter(mock_rows)

    mock_session.execute = AsyncMock(side_effect=[count_result, main_result])

    repo = SpeakerRepositoryImpl(mock_session, mock_model)

    # Act
    result, total = await repo.get_all_with_conversation_count(offset=20, limit=20)

    # Assert
    assert len(result) == 20
    assert total == 100

    # Verify SQL query contains correct LIMIT and OFFSET
    sql_call = mock_session.execute.call_args_list[1]
    sql_text = str(sql_call[0][0])
    assert "LIMIT :limit" in sql_text
    assert "OFFSET :offset" in sql_text
    assert sql_call[0][1] == {"limit": 20, "offset": 20}
