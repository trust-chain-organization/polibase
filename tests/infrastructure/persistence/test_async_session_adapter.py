"""Tests for AsyncSessionAdapter."""

from unittest.mock import Mock

import pytest
from sqlalchemy.orm import Session

from src.infrastructure.persistence.async_session_adapter import AsyncSessionAdapter


@pytest.fixture
def mock_sync_session():
    """Create mock sync session."""
    return Mock(spec=Session)


@pytest.fixture
def async_session_adapter(mock_sync_session):
    """Create AsyncSessionAdapter with mock sync session."""
    return AsyncSessionAdapter(mock_sync_session)


def test_add(async_session_adapter, mock_sync_session):
    """Test add method delegates to sync session."""
    instance = Mock()
    async_session_adapter.add(instance)
    mock_sync_session.add.assert_called_once_with(instance)


def test_add_all(async_session_adapter, mock_sync_session):
    """Test add_all method delegates to sync session."""
    instances = [Mock(), Mock(), Mock()]
    async_session_adapter.add_all(instances)
    mock_sync_session.add_all.assert_called_once_with(instances)


@pytest.mark.asyncio
async def test_commit(async_session_adapter, mock_sync_session):
    """Test commit method delegates to sync session."""
    await async_session_adapter.commit()
    mock_sync_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_rollback(async_session_adapter, mock_sync_session):
    """Test rollback method delegates to sync session."""
    await async_session_adapter.rollback()
    mock_sync_session.rollback.assert_called_once()


@pytest.mark.asyncio
async def test_close(async_session_adapter, mock_sync_session):
    """Test close method delegates to sync session."""
    await async_session_adapter.close()
    mock_sync_session.close.assert_called_once()


@pytest.mark.asyncio
async def test_flush(async_session_adapter, mock_sync_session):
    """Test flush method delegates to sync session."""
    await async_session_adapter.flush()
    mock_sync_session.flush.assert_called_once()


@pytest.mark.asyncio
async def test_refresh(async_session_adapter, mock_sync_session):
    """Test refresh method delegates to sync session."""
    instance = Mock()
    await async_session_adapter.refresh(instance)
    mock_sync_session.refresh.assert_called_once_with(instance)


@pytest.mark.asyncio
async def test_execute_without_params(async_session_adapter, mock_sync_session):
    """Test execute method without parameters."""
    statement = "SELECT * FROM table"
    mock_result = Mock()
    mock_sync_session.execute.return_value = mock_result

    result = await async_session_adapter.execute(statement)

    assert result == mock_result
    mock_sync_session.execute.assert_called_once_with(statement)


@pytest.mark.asyncio
async def test_execute_with_params(async_session_adapter, mock_sync_session):
    """Test execute method with parameters."""
    statement = "SELECT * FROM table WHERE id = :id"
    params = {"id": 123}
    mock_result = Mock()
    mock_sync_session.execute.return_value = mock_result

    result = await async_session_adapter.execute(statement, params)

    assert result == mock_result
    mock_sync_session.execute.assert_called_once_with(statement, params)
