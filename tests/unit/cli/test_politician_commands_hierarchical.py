"""Unit tests for hierarchical scraping in politician_commands.py

This module tests the _async_scrape_politicians_hierarchical method
to ensure correct state creation, parameter handling, and error recovery.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.cli_package.commands.politician_commands import PoliticianCommands
from src.domain.entities.party_scraping_state import PartyScrapingState


class TestAsyncScrapePoliticiansHierarchical:
    """Unit tests for _async_scrape_politicians_hierarchical method."""

    @pytest.mark.asyncio
    async def test_creates_correct_initial_state(self):
        """Test that method creates correct PartyScrapingState."""
        # Setup
        mock_party = MagicMock()
        mock_party.id = 1
        mock_party.name = "Test Party"
        mock_party.members_list_url = "https://example.com/members"

        mock_agent = AsyncMock()
        mock_container = MagicMock()
        mock_container.use_cases.party_scraping_agent.return_value = mock_agent

        # Capture the state passed to agent
        captured_state = None

        async def capture_state(state):
            nonlocal captured_state
            captured_state = state
            # Return a mock result state
            mock_result = MagicMock()
            mock_result.error_message = None
            mock_result.extracted_members = []
            mock_result.visited_urls = []
            return mock_result

        mock_agent.scrape.side_effect = capture_state

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

            # Execute
            await PoliticianCommands._async_scrape_politicians_hierarchical(
                party_id=1, all_parties=False, dry_run=True, max_depth=5
            )

            # Assert state was created correctly
            assert captured_state is not None
            assert isinstance(captured_state, PartyScrapingState)
            assert captured_state.party_id == 1
            assert captured_state.party_name == "Test Party"
            assert captured_state.current_url == "https://example.com/members"
            assert captured_state.max_depth == 5

    @pytest.mark.asyncio
    async def test_handles_single_party(self):
        """Test processing of a single party."""
        mock_party = MagicMock(
            id=42, name="Single Party", members_list_url="https://single.com"
        )

        mock_agent = AsyncMock()
        mock_state = MagicMock()
        mock_state.error_message = None
        mock_state.extracted_members = []
        mock_state.visited_urls = ["https://single.com"]
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
            mock_conn.execute.return_value.fetchall.return_value = [mock_party]

            # Execute
            await PoliticianCommands._async_scrape_politicians_hierarchical(
                party_id=42, all_parties=False, dry_run=True, max_depth=3
            )

            # Verify agent was called exactly once
            assert mock_agent.scrape.call_count == 1

    @pytest.mark.asyncio
    async def test_handles_multiple_parties(self):
        """Test processing of multiple parties in sequence."""
        parties = [
            MagicMock(id=1, name="Party A", members_list_url="https://a.com"),
            MagicMock(id=2, name="Party B", members_list_url="https://b.com"),
            MagicMock(id=3, name="Party C", members_list_url="https://c.com"),
        ]

        mock_agent = AsyncMock()

        # Track which parties were processed
        processed_parties = []

        async def track_processing(state):
            processed_parties.append(state.party_id)
            # Return mock state
            mock_result = MagicMock()
            mock_result.error_message = None
            mock_result.extracted_members = []
            mock_result.visited_urls = [state.current_url]
            return mock_result

        mock_agent.scrape.side_effect = track_processing

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
            mock_conn.execute.return_value.fetchall.return_value = parties

            # Execute
            await PoliticianCommands._async_scrape_politicians_hierarchical(
                party_id=None, all_parties=True, dry_run=True, max_depth=3
            )

            # Verify all parties were processed in order
            assert processed_parties == [1, 2, 3]
            assert mock_agent.scrape.call_count == 3

    @pytest.mark.asyncio
    async def test_handles_no_parties_gracefully(self):
        """Test behavior when no parties have members_list_url."""
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
            mock_conn.execute.return_value.fetchall.return_value = []

            # Execute - should not raise exception
            await PoliticianCommands._async_scrape_politicians_hierarchical(
                party_id=None, all_parties=True, dry_run=True, max_depth=3
            )

            # Verify agent was never called
            assert mock_agent.scrape.call_count == 0

    @pytest.mark.asyncio
    async def test_passes_max_depth_to_agent(self):
        """Test that max_depth parameter is correctly passed to Agent."""
        mock_party = MagicMock(
            id=1, name="Test Party", members_list_url="https://example.com"
        )

        mock_agent = AsyncMock()

        # Capture initial state to verify max_depth
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

            # Test with max_depth=0
            await PoliticianCommands._async_scrape_politicians_hierarchical(
                party_id=1, all_parties=False, dry_run=True, max_depth=0
            )

            # Verify max_depth=0 was passed to Agent
            assert captured_state.max_depth == 0

            # Test with max_depth=10
            await PoliticianCommands._async_scrape_politicians_hierarchical(
                party_id=1, all_parties=False, dry_run=True, max_depth=10
            )

            # Verify max_depth=10 was passed to Agent
            assert captured_state.max_depth == 10

    @pytest.mark.asyncio
    async def test_handles_agent_exceptions(self):
        """Test that Agent exceptions are handled gracefully."""
        mock_party = MagicMock(
            id=1, name="Test Party", members_list_url="https://example.com"
        )

        mock_agent = AsyncMock()
        mock_agent.scrape.side_effect = RuntimeError("Unexpected scraping error")

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

            # Should raise - error propagates to caller
            with pytest.raises(RuntimeError, match="Unexpected scraping error"):
                await PoliticianCommands._async_scrape_politicians_hierarchical(
                    party_id=1, all_parties=False, dry_run=True, max_depth=3
                )

    @pytest.mark.asyncio
    async def test_handles_database_connection_failures(self):
        """Test that database connection errors are handled gracefully."""
        with patch("src.config.database.get_db_engine") as mock_engine:
            mock_engine.side_effect = RuntimeError("Database connection failed")

            # Should raise - database errors should propagate
            with pytest.raises(RuntimeError, match="Database connection failed"):
                await PoliticianCommands._async_scrape_politicians_hierarchical(
                    party_id=1, all_parties=False, dry_run=True, max_depth=3
                )

    @pytest.mark.asyncio
    async def test_respects_dry_run_mode(self):
        """Test that dry_run=True prevents database writes."""
        mock_party = MagicMock(
            id=1, name="Test Party", members_list_url="https://example.com/members"
        )

        mock_agent = AsyncMock()
        mock_state = MagicMock()
        mock_state.error_message = None
        mock_state.extracted_members = [{"name": "Test Member"}]
        mock_state.visited_urls = ["https://example.com/members"]
        mock_agent.scrape.return_value = mock_state

        mock_container = MagicMock()
        mock_container.use_cases.party_scraping_agent.return_value = mock_agent

        with (
            patch("src.config.database.get_db_engine") as mock_engine,
            patch(
                "src.infrastructure.di.container.get_container",
                return_value=mock_container,
            ),
            patch("src.config.database.get_db_session") as mock_session,
            patch.dict("os.environ", {"STREAMLIT_RUNNING": "true"}),
        ):
            mock_conn = MagicMock()
            mock_engine.return_value.connect.return_value.__enter__.return_value = (
                mock_conn
            )
            mock_conn.execute.return_value.fetchall.return_value = [mock_party]

            # Execute in dry run mode
            await PoliticianCommands._async_scrape_politicians_hierarchical(
                party_id=1, all_parties=False, dry_run=True, max_depth=3
            )

            # Verify database session was NEVER created
            mock_session.assert_not_called()
