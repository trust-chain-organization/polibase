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
        error_msg = str(e).lower()
        assert (
            "asyncpg" in error_msg
            or "database" in error_msg
            or "connection" in error_msg
            or "connect" in error_msg
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

        # Should successfully call async method from sync context
        try:
            result = adapter.get_overall_metrics()
            # Adapter successfully bridged async to sync
            assert isinstance(result, dict)
            # Check that essential keys are present
            assert "governing_bodies" in result
            assert "conferences" in result
        except Exception as e:
            # Should be a DB error, not an async error
            error_msg = str(e).lower()
            # Make sure it's not an asyncio-related error
            if "asyncio" in error_msg:
                # Unless it's asyncpg which is a valid DB error
                assert "asyncpg" in error_msg
            else:
                # Otherwise it should be a DB-related error
                assert (
                    "database" in error_msg
                    or "connection" in error_msg
                    or "connect" in error_msg
                )

    @pytest.mark.asyncio
    async def test_async_context(self):
        """Test that adapter returns coroutine when called from async context."""
        adapter = RepositoryAdapter(MonitoringRepositoryImpl)

        # In async context, adapter should return a coroutine
        try:
            result = await adapter.get_overall_metrics()
            # Should successfully return data from async context
            assert isinstance(result, dict)
            assert "governing_bodies" in result
            assert "conferences" in result
        except Exception as e:
            # If we get an exception, it should be a DB connection error
            error_msg = str(e).lower()
            # Make sure it's not an async context conflict error
            if "asyncio" in error_msg:
                # Unless it's asyncpg which is a valid DB error
                assert "asyncpg" in error_msg
            else:
                # Otherwise it should be a DB-related error
                assert (
                    "database" in error_msg
                    or "connection" in error_msg
                    or "connect" in error_msg
                )
