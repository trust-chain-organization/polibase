"""Error handling tests for hierarchical politician scraping.

This module tests error scenarios to ensure the CLI handles failures gracefully
and provides appropriate error messages to users.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.interfaces.cli.commands.politician_commands import PoliticianCommands


class TestErrorHandling:
    """Test error handling in hierarchical scraping."""

    @pytest.mark.asyncio
    async def test_agent_initialization_failure(self):
        """Test handling when DI container fails to initialize Agent."""
        with (
            patch("src.infrastructure.config.database.get_db_engine") as mock_engine,
            patch("src.infrastructure.di.container.get_container") as mock_container,
        ):
            # Setup database mock
            mock_conn = MagicMock()
            mock_engine.return_value.connect.return_value.__enter__.return_value = (
                mock_conn
            )
            mock_party = MagicMock(
                id=1, name="Test", members_list_url="https://example.com"
            )
            mock_conn.execute.return_value.fetchall.return_value = [mock_party]

            # Container fails to provide agent
            mock_container.return_value.use_cases.party_scraping_agent.side_effect = (
                RuntimeError("Container initialization failed")
            )

            with (
                patch.dict("os.environ", {"STREAMLIT_RUNNING": "true"}),
                pytest.raises(RuntimeError, match="Container initialization failed"),
            ):
                await PoliticianCommands._async_scrape_politicians_hierarchical(
                    party_id=1, all_parties=False, dry_run=True, max_depth=3
                )

    @pytest.mark.asyncio
    async def test_agent_scrape_raises_exception(self):
        """Test handling when Agent.scrape() raises unexpected exception."""
        mock_agent = AsyncMock()
        mock_agent.scrape.side_effect = RuntimeError("Unexpected scraping error")

        mock_container = MagicMock()
        mock_container.use_cases.party_scraping_agent.return_value = mock_agent

        mock_party = MagicMock(
            id=1, name="Test Party", members_list_url="https://example.com"
        )

        with (
            patch("src.infrastructure.config.database.get_db_engine") as mock_engine,
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

            # Should propagate error
            with pytest.raises(RuntimeError, match="Unexpected scraping error"):
                await PoliticianCommands._async_scrape_politicians_hierarchical(
                    party_id=1, all_parties=False, dry_run=True, max_depth=3
                )

    @pytest.mark.asyncio
    async def test_bulk_create_raises_database_error(self):
        """Test handling when repository bulk_create fails."""
        mock_party = MagicMock(
            id=1, name="Test Party", members_list_url="https://example.com"
        )

        mock_agent = AsyncMock()
        mock_state = MagicMock()
        mock_state.error_message = None
        mock_state.extracted_members = [{"name": "Test Member"}]
        mock_state.visited_urls = ["https://example.com"]
        mock_agent.scrape.return_value = mock_state

        mock_container = MagicMock()
        mock_container.use_cases.party_scraping_agent.return_value = mock_agent

        with (
            patch("src.infrastructure.config.database.get_db_engine") as mock_engine,
            patch(
                "src.infrastructure.di.container.get_container",
                return_value=mock_container,
            ),
            patch("src.infrastructure.config.database.get_db_session"),
            patch(
                "src.infrastructure.persistence.politician_repository_sync_impl.PoliticianRepositorySyncImpl"
            ) as mock_repo_class,
            patch.dict("os.environ", {"STREAMLIT_RUNNING": "true"}),
        ):
            mock_conn = MagicMock()
            mock_engine.return_value.connect.return_value.__enter__.return_value = (
                mock_conn
            )
            mock_conn.execute.return_value.fetchall.return_value = [mock_party]

            mock_repo = MagicMock()
            mock_repo.bulk_create_politicians_sync.side_effect = Exception(
                "Database constraint violation"
            )
            mock_repo_class.return_value = mock_repo

            # Should raise - database errors should propagate
            with pytest.raises(Exception, match="Database constraint violation"):
                await PoliticianCommands._async_scrape_politicians_hierarchical(
                    party_id=1, all_parties=False, dry_run=False, max_depth=3
                )

    @pytest.mark.asyncio
    async def test_database_query_failure(self):
        """Test handling when database party query fails."""
        with patch("src.infrastructure.config.database.get_db_engine") as mock_engine:
            mock_conn = MagicMock()
            mock_engine.return_value.connect.return_value.__enter__.return_value = (
                mock_conn
            )

            # Query execution fails
            mock_conn.execute.side_effect = Exception("Query execution failed")

            with (
                patch.dict("os.environ", {"STREAMLIT_RUNNING": "true"}),
                pytest.raises(Exception, match="Query execution failed"),
            ):
                await PoliticianCommands._async_scrape_politicians_hierarchical(
                    party_id=1, all_parties=False, dry_run=True, max_depth=3
                )

    @pytest.mark.asyncio
    async def test_handles_empty_members_list_url(self):
        """Test handling when party has None members_list_url."""
        # SQL query filters parties with NULL members_list_url
        # So this tests the SQL filtering behavior
        mock_agent = AsyncMock()
        mock_container = MagicMock()
        mock_container.use_cases.party_scraping_agent.return_value = mock_agent

        with (
            patch("src.infrastructure.config.database.get_db_engine") as mock_engine,
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
            # SQL query filters out parties with NULL members_list_url
            # So empty result is returned
            mock_conn.execute.return_value.fetchall.return_value = []

            # Should handle gracefully - no parties to process
            await PoliticianCommands._async_scrape_politicians_hierarchical(
                party_id=1, all_parties=False, dry_run=True, max_depth=3
            )

            # Agent was never called because no parties matched
            assert not mock_agent.scrape.called

    @pytest.mark.asyncio
    async def test_handles_malformed_extracted_data(self):
        """Test handling when Agent returns malformed member data."""
        mock_party = MagicMock(
            id=1, name="Test Party", members_list_url="https://example.com"
        )

        mock_agent = AsyncMock()
        mock_state = MagicMock()
        mock_state.error_message = None
        # Malformed data: missing 'name' field
        mock_state.extracted_members = [{"invalid_field": "value"}]
        mock_state.visited_urls = ["https://example.com"]
        mock_agent.scrape.return_value = mock_state

        mock_container = MagicMock()
        mock_container.use_cases.party_scraping_agent.return_value = mock_agent

        with (
            patch("src.infrastructure.config.database.get_db_engine") as mock_engine,
            patch(
                "src.infrastructure.di.container.get_container",
                return_value=mock_container,
            ),
            patch("src.infrastructure.config.database.get_db_session"),
            patch(
                "src.infrastructure.persistence.politician_repository_sync_impl.PoliticianRepositorySyncImpl"
            ) as mock_repo_class,
            patch.dict("os.environ", {"STREAMLIT_RUNNING": "true"}),
        ):
            mock_conn = MagicMock()
            mock_engine.return_value.connect.return_value.__enter__.return_value = (
                mock_conn
            )
            mock_conn.execute.return_value.fetchall.return_value = [mock_party]

            mock_repo = MagicMock()
            # Repository handles it (might succeed or fail depending on schema)
            mock_repo.bulk_create_politicians_sync.return_value = {
                "created": [],
                "updated": [],
                "errors": [{"error": "Missing name field"}],
            }
            mock_repo_class.return_value = mock_repo

            # Should not crash - repo handles malformed data
            await PoliticianCommands._async_scrape_politicians_hierarchical(
                party_id=1, all_parties=False, dry_run=False, max_depth=3
            )

            # Verify repo was called despite malformed data
            assert mock_repo.bulk_create_politicians_sync.called

    @pytest.mark.asyncio
    async def test_handles_partial_agent_error_with_results(self):
        """Test handling when Agent has error but also extracted some members."""
        mock_party = MagicMock(
            id=1, name="Test Party", members_list_url="https://example.com"
        )

        mock_agent = AsyncMock()
        mock_state = MagicMock()
        # Agent encountered error but still extracted some members
        mock_state.error_message = "Timeout after processing 2 pages"
        mock_state.extracted_members = [
            {"name": "Member 1"},
            {"name": "Member 2"},
        ]
        mock_state.visited_urls = ["https://example.com", "https://example.com/page2"]
        mock_agent.scrape.return_value = mock_state

        mock_container = MagicMock()
        mock_container.use_cases.party_scraping_agent.return_value = mock_agent

        with (
            patch("src.infrastructure.config.database.get_db_engine") as mock_engine,
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

            # Should handle gracefully - shows error but continues to next party
            await PoliticianCommands._async_scrape_politicians_hierarchical(
                party_id=1, all_parties=False, dry_run=True, max_depth=3
            )

            # Agent was called and returned results despite error
            assert mock_agent.scrape.called
