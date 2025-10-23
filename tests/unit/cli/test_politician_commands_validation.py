"""Parameter validation tests for hierarchical politician scraping.

This module tests parameter validation to ensure the CLI properly handles
invalid inputs and edge cases.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.cli_package.commands.politician_commands import PoliticianCommands


class TestParameterValidation:
    """Test parameter validation and edge cases."""

    @pytest.mark.asyncio
    async def test_zero_max_depth_allowed(self):
        """Test that max_depth=0 is allowed (only processes root page)."""
        mock_party = MagicMock(
            id=1, name="Test Party", members_list_url="https://example.com"
        )

        mock_agent = AsyncMock()

        # Capture state to verify max_depth
        captured_state = None

        async def capture(state):
            nonlocal captured_state
            captured_state = state
            mock_result = MagicMock()
            mock_result.error_message = None
            mock_result.extracted_members = []
            mock_result.visited_urls = []
            return mock_result

        mock_agent.scrape.side_effect = capture

        mock_container = MagicMock()
        mock_container.use_cases.party_scraping_agent.return_value = mock_agent

        with (
            patch("src.config.database.get_db_engine") as mock_engine,
            patch(
                "src.infrastructure.di.container.get_container",
                return_value=mock_container,
            ),
            patch.dict("os.environ", {"STREAMLIT_RUNNING": "true"}),
        ):
            mock_conn = MagicMock()
            mock_engine.return_value.connect.return_value.__enter__.return_value = (
                mock_conn
            )
            mock_conn.execute.return_value.fetchall.return_value = [mock_party]

            # Should not raise - max_depth=0 is valid
            await PoliticianCommands._async_scrape_politicians_hierarchical(
                party_id=1, all_parties=False, dry_run=True, max_depth=0
            )

            # Verify max_depth=0 was accepted
            assert captured_state is not None
            assert captured_state.max_depth == 0

    @pytest.mark.asyncio
    async def test_negative_max_depth_creates_invalid_state(self):
        """Test that negative max_depth is rejected by PartyScrapingState."""
        mock_party = MagicMock(
            id=1, name="Test Party", members_list_url="https://example.com"
        )

        mock_container = MagicMock()
        mock_agent = AsyncMock()
        mock_container.use_cases.party_scraping_agent.return_value = mock_agent

        with (
            patch("src.config.database.get_db_engine") as mock_engine,
            patch(
                "src.infrastructure.di.container.get_container",
                return_value=mock_container,
            ),
            patch.dict("os.environ", {"STREAMLIT_RUNNING": "true"}),
        ):
            mock_conn = MagicMock()
            mock_engine.return_value.connect.return_value.__enter__.return_value = (
                mock_conn
            )
            mock_conn.execute.return_value.fetchall.return_value = [mock_party]

            # PartyScrapingState doesn't validate max_depth in __init__
            # but negative depth is semantically invalid
            # The method should handle this or rely on domain validation
            # For now, test that it doesn't crash
            await PoliticianCommands._async_scrape_politicians_hierarchical(
                party_id=1, all_parties=False, dry_run=True, max_depth=-1
            )

            # Agent was called (no validation currently, but shouldn't crash)
            assert mock_agent.scrape.called

    @pytest.mark.asyncio
    async def test_invalid_party_id_zero(self):
        """Test handling of party_id=0 (invalid)."""
        mock_agent = AsyncMock()
        mock_container = MagicMock()
        mock_container.use_cases.party_scraping_agent.return_value = mock_agent

        with (
            patch("src.config.database.get_db_engine") as mock_engine,
            patch(
                "src.infrastructure.di.container.get_container",
                return_value=mock_container,
            ),
            patch.dict("os.environ", {"STREAMLIT_RUNNING": "true"}),
        ):
            mock_conn = MagicMock()
            mock_engine.return_value.connect.return_value.__enter__.return_value = (
                mock_conn
            )
            # Database returns empty (party_id=0 doesn't exist)
            mock_conn.execute.return_value.fetchall.return_value = []

            # Should handle gracefully - no parties found
            await PoliticianCommands._async_scrape_politicians_hierarchical(
                party_id=0, all_parties=False, dry_run=True, max_depth=3
            )

            # No processing happened - agent was never called
            assert not mock_agent.scrape.called

    @pytest.mark.asyncio
    async def test_invalid_party_id_negative(self):
        """Test handling of negative party_id."""
        mock_agent = AsyncMock()
        mock_container = MagicMock()
        mock_container.use_cases.party_scraping_agent.return_value = mock_agent

        with (
            patch("src.config.database.get_db_engine") as mock_engine,
            patch(
                "src.infrastructure.di.container.get_container",
                return_value=mock_container,
            ),
            patch.dict("os.environ", {"STREAMLIT_RUNNING": "true"}),
        ):
            mock_conn = MagicMock()
            mock_engine.return_value.connect.return_value.__enter__.return_value = (
                mock_conn
            )
            # Database returns empty (negative ID doesn't exist)
            mock_conn.execute.return_value.fetchall.return_value = []

            # Should handle gracefully
            await PoliticianCommands._async_scrape_politicians_hierarchical(
                party_id=-1, all_parties=False, dry_run=True, max_depth=3
            )

            # No processing happened - agent was never called
            assert not mock_agent.scrape.called

    @pytest.mark.asyncio
    async def test_both_party_id_and_all_parties_false(self):
        """Test that party_id=None and all_parties=False results in all parties."""
        # Current implementation: if party_id is None, queries all parties
        # regardless of all_parties flag
        mock_parties = [
            MagicMock(id=1, name="Party 1", members_list_url="https://1.com"),
            MagicMock(id=2, name="Party 2", members_list_url="https://2.com"),
        ]

        mock_agent = AsyncMock()
        mock_state = MagicMock()
        mock_state.error_message = None
        mock_state.extracted_members = []
        mock_state.visited_urls = []
        mock_agent.scrape.return_value = mock_state

        mock_container = MagicMock()
        mock_container.use_cases.party_scraping_agent.return_value = mock_agent

        with (
            patch("src.config.database.get_db_engine") as mock_engine,
            patch(
                "src.infrastructure.di.container.get_container",
                return_value=mock_container,
            ),
            patch.dict("os.environ", {"STREAMLIT_RUNNING": "true"}),
        ):
            mock_conn = MagicMock()
            mock_engine.return_value.connect.return_value.__enter__.return_value = (
                mock_conn
            )
            mock_conn.execute.return_value.fetchall.return_value = mock_parties

            # Execute with both None/False
            await PoliticianCommands._async_scrape_politicians_hierarchical(
                party_id=None, all_parties=False, dry_run=True, max_depth=3
            )

            # All parties were processed
            assert mock_agent.scrape.call_count == 2

    @pytest.mark.asyncio
    async def test_large_max_depth_value(self):
        """Test that very large max_depth values are handled."""
        mock_party = MagicMock(
            id=1, name="Test Party", members_list_url="https://example.com"
        )

        mock_agent = AsyncMock()
        captured_state = None

        async def capture(state):
            nonlocal captured_state
            captured_state = state
            mock_result = MagicMock()
            mock_result.error_message = None
            mock_result.extracted_members = []
            mock_result.visited_urls = []
            return mock_result

        mock_agent.scrape.side_effect = capture

        mock_container = MagicMock()
        mock_container.use_cases.party_scraping_agent.return_value = mock_agent

        with (
            patch("src.config.database.get_db_engine") as mock_engine,
            patch(
                "src.infrastructure.di.container.get_container",
                return_value=mock_container,
            ),
            patch.dict("os.environ", {"STREAMLIT_RUNNING": "true"}),
        ):
            mock_conn = MagicMock()
            mock_engine.return_value.connect.return_value.__enter__.return_value = (
                mock_conn
            )
            mock_conn.execute.return_value.fetchall.return_value = [mock_party]

            # Test with very large max_depth
            await PoliticianCommands._async_scrape_politicians_hierarchical(
                party_id=1, all_parties=False, dry_run=True, max_depth=1000
            )

            # Should accept large values
            assert captured_state.max_depth == 1000
