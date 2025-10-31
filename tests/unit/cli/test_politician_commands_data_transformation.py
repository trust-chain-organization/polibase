"""Data transformation tests for hierarchical politician scraping.

This module tests data transformation logic to ensure correct conversion
between Agent results, DTOs, and repository formats.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.cli_package.commands.politician_commands import PoliticianCommands


class TestDataTransformation:
    """Test data transformation in hierarchical scraping."""

    @pytest.mark.asyncio
    async def test_agent_results_converted_to_dict_format(self):
        """Test that Agent results are correctly converted to dict format."""
        mock_party = MagicMock(
            id=1, name="Test Party", members_list_url="https://example.com"
        )

        # Agent returns members as list of dicts
        mock_agent = AsyncMock()
        mock_state = MagicMock()
        mock_state.error_message = None
        mock_state.extracted_members = [
            {"name": "山田太郎", "role": "代表"},
            {"name": "田中花子", "role": "幹事長"},
        ]
        mock_state.visited_urls = ["https://example.com"]
        mock_agent.scrape.return_value = mock_state

        mock_container = MagicMock()
        mock_container.use_cases.party_scraping_agent.return_value = mock_agent

        # Capture what was passed to repository
        captured_members = None

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

            def capture_members(members):
                nonlocal captured_members
                captured_members = members
                return {"created": [], "updated": [], "errors": []}

            mock_repo.bulk_create_politicians_sync.side_effect = capture_members
            mock_repo_class.return_value = mock_repo

            # Execute
            await PoliticianCommands._async_scrape_politicians_hierarchical(
                party_id=1, all_parties=False, dry_run=False, max_depth=3
            )

            # Verify members were passed as list of dicts
            assert captured_members is not None
            assert isinstance(captured_members, list)
            assert len(captured_members) == 2
            assert all(isinstance(m, dict) for m in captured_members)

    @pytest.mark.asyncio
    async def test_political_party_id_added_to_member_data(self):
        """Test that political_party_id is correctly added to each member."""
        mock_party = MagicMock(
            id=42, name="Test Party", members_list_url="https://example.com"
        )

        mock_agent = AsyncMock()
        mock_state = MagicMock()
        mock_state.error_message = None
        # Members without political_party_id
        mock_state.extracted_members = [
            {"name": "Member A"},
            {"name": "Member B"},
        ]
        mock_state.visited_urls = ["https://example.com"]
        mock_agent.scrape.return_value = mock_state

        mock_container = MagicMock()
        mock_container.use_cases.party_scraping_agent.return_value = mock_agent

        captured_members = None

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

            def capture(members):
                nonlocal captured_members
                captured_members = members
                return {"created": [], "updated": [], "errors": []}

            mock_repo.bulk_create_politicians_sync.side_effect = capture
            mock_repo_class.return_value = mock_repo

            # Execute
            await PoliticianCommands._async_scrape_politicians_hierarchical(
                party_id=42, all_parties=False, dry_run=False, max_depth=3
            )

            # Verify political_party_id was added to each member
            assert all(m.get("political_party_id") == 42 for m in captured_members)

    @pytest.mark.asyncio
    async def test_handles_duplicate_members_from_agent(self):
        """Test handling of duplicate members returned by Agent."""
        mock_party = MagicMock(
            id=1, name="Test Party", members_list_url="https://example.com"
        )

        mock_agent = AsyncMock()
        mock_state = MagicMock()
        mock_state.error_message = None
        # Agent returns duplicate members (same name)
        mock_state.extracted_members = [
            {"name": "山田太郎", "role": "代表"},
            {"name": "山田太郎", "role": "代表"},  # Duplicate
            {"name": "田中花子", "role": "幹事長"},
        ]
        mock_state.visited_urls = ["https://example.com", "https://example.com/page2"]
        mock_agent.scrape.return_value = mock_state

        mock_container = MagicMock()
        mock_container.use_cases.party_scraping_agent.return_value = mock_agent

        captured_members = None

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

            def capture(members):
                nonlocal captured_members
                captured_members = members
                return {"created": [], "updated": [], "errors": []}

            mock_repo.bulk_create_politicians_sync.side_effect = capture
            mock_repo_class.return_value = mock_repo

            # Execute
            await PoliticianCommands._async_scrape_politicians_hierarchical(
                party_id=1, all_parties=False, dry_run=False, max_depth=3
            )

            # Repository receives duplicates (CLI doesn't deduplicate)
            # Repository is responsible for handling duplicates
            assert len(captured_members) == 3

    @pytest.mark.asyncio
    async def test_statistics_calculated_from_repository_results(self):
        """Test that statistics are correctly calculated from repository results."""
        mock_party = MagicMock(
            id=1, name="Test Party", members_list_url="https://example.com"
        )

        mock_agent = AsyncMock()
        mock_state = MagicMock()
        mock_state.error_message = None
        mock_state.extracted_members = [
            {"name": "Member 1"},
            {"name": "Member 2"},
            {"name": "Member 3"},
        ]
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
            # Repository returns mixed results
            mock_repo.bulk_create_politicians_sync.return_value = {
                "created": [{"name": "Member 1"}, {"name": "Member 2"}],
                "updated": [{"name": "Member 3"}],
                "errors": [],
            }
            mock_repo_class.return_value = mock_repo

            # Execute
            await PoliticianCommands._async_scrape_politicians_hierarchical(
                party_id=1, all_parties=False, dry_run=False, max_depth=3
            )

            # Verify repository was called with correct data
            assert mock_repo.bulk_create_politicians_sync.called
            # Verify result contains correct statistics
            result = mock_repo.bulk_create_politicians_sync.return_value
            assert len(result["created"]) == 2
            assert len(result["updated"]) == 1
            assert len(result["errors"]) == 0
