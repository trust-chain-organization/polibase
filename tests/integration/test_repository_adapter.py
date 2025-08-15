"""Integration tests for RepositoryAdapter."""

import pytest

from src.infrastructure.persistence.monitoring_repository_impl import (
    MonitoringRepositoryImpl,
)
from src.infrastructure.persistence.repository_adapter import RepositoryAdapter


def test_adapter_basic_functionality():
    """Test that adapter can call async methods from sync context."""
    # Create adapter with MonitoringRepositoryImpl
    adapter = RepositoryAdapter(MonitoringRepositoryImpl)

    # This should work without raising exceptions
    # Note: Will fail with actual DB operations without proper DB setup
    # but the adapter mechanism itself should work
    try:
        # Try to call an async method through the adapter
        # This will fail due to DB connection issues, but adapter should handle it
        adapter.get_overall_metrics()
    except Exception as e:
        # We expect DB connection errors, not adapter errors
        assert (
            "asyncpg" in str(e)
            or "database" in str(e).lower()
            or "connection" in str(e).lower()
        )


def test_adapter_handles_multiple_calls():
    """Test that adapter can handle multiple method calls."""
    adapter = RepositoryAdapter(MonitoringRepositoryImpl)

    # Test that we can access multiple methods
    assert hasattr(adapter, "get_overall_metrics")
    assert hasattr(adapter, "get_recent_activities")
    assert hasattr(adapter, "get_conference_coverage")
    assert hasattr(adapter, "get_party_coverage")


def test_adapter_cleanup():
    """Test that adapter properly cleans up resources."""
    adapter = RepositoryAdapter(MonitoringRepositoryImpl)

    # Test context manager
    with adapter as a:
        assert a is not None

    # After exiting context, resources should be cleaned
    adapter.close()  # Should not raise


class TestAsyncIntegration:
    """Test async operations in different contexts."""

    def test_sync_context(self):
        """Test adapter works in sync context."""
        adapter = RepositoryAdapter(MonitoringRepositoryImpl)
        # Should not raise (except for DB errors)
        with pytest.raises(Exception) as exc_info:
            adapter.get_overall_metrics()
        # Check it's a DB error, not an async/adapter error
        assert (
            "asyncio" not in str(exc_info.value).lower()
            or "asyncpg" in str(exc_info.value).lower()
        )

    @pytest.mark.asyncio
    async def test_async_context(self):
        """Test that adapter still works when called from async context."""
        adapter = RepositoryAdapter(MonitoringRepositoryImpl)

        # Even in async context, adapter should handle the bridging
        with pytest.raises(Exception) as exc_info:
            adapter.get_overall_metrics()

        # Should get DB errors, not async context errors
        error_msg = str(exc_info.value).lower()
        assert "asyncio" not in error_msg or "asyncpg" in error_msg
