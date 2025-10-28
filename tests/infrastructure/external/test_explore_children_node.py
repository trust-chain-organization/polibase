"""Tests for explore_children_node."""

from unittest.mock import AsyncMock, Mock

import pytest

from src.infrastructure.external.langgraph_nodes.explore_children_node import (
    create_explore_children_node,
)


class TestExploreChildrenNode:
    """Test cases for explore_children_node."""

    @pytest.fixture
    def mock_scraper(self):
        """Create mock web scraper service."""
        scraper = Mock()
        scraper.fetch_html = AsyncMock()
        return scraper

    @pytest.fixture
    def mock_link_analyzer(self):
        """Create mock link analyzer service."""
        analyzer = Mock()
        analyzer.analyze_member_list_links = AsyncMock()
        return analyzer

    @pytest.fixture
    def explore_children_node(self, mock_scraper, mock_link_analyzer):
        """Create explore_children_node function."""
        return create_explore_children_node(
            scraper=mock_scraper,
            link_analyzer=mock_link_analyzer,
        )

    @pytest.mark.asyncio
    async def test_prefecture_links_added_to_pending_urls(
        self, explore_children_node, mock_scraper, mock_link_analyzer
    ):
        """Prefecture links should be correctly added to pending_urls."""
        # Arrange
        mock_scraper.fetch_html.return_value = "<html>...</html>"
        mock_link_analyzer.analyze_member_list_links.return_value = [
            "https://jcp.or.jp/hokkaido",
            "https://jcp.or.jp/tokyo",
        ]

        state = {
            "current_url": "https://jcp.or.jp/giin/",
            "party_name": "日本共産党",
            "depth": 0,
            "max_depth": 2,
            "pending_urls": [],
            "visited_urls": set(),
        }

        # Act
        result = await explore_children_node(state)

        # Assert
        assert len(result["pending_urls"]) == 2
        # URLs should be normalized and added with depth + 1
        pending_urls_dict = dict(result["pending_urls"])
        assert "https://jcp.or.jp/hokkaido" in pending_urls_dict
        assert "https://jcp.or.jp/tokyo" in pending_urls_dict
        assert pending_urls_dict["https://jcp.or.jp/hokkaido"] == 1
        assert pending_urls_dict["https://jcp.or.jp/tokyo"] == 1

    @pytest.mark.asyncio
    async def test_depth_limit_enforced(
        self, explore_children_node, mock_scraper, mock_link_analyzer
    ):
        """URLs beyond max_depth should not be added to pending_urls."""
        # Arrange
        mock_scraper.fetch_html.return_value = "<html>...</html>"
        mock_link_analyzer.analyze_member_list_links.return_value = [
            "https://jcp.or.jp/hokkaido",
            "https://jcp.or.jp/tokyo",
        ]

        state = {
            "current_url": "https://jcp.or.jp/giin/",
            "party_name": "日本共産党",
            "depth": 2,  # Already at max depth
            "max_depth": 2,
            "pending_urls": [],
            "visited_urls": set(),
        }

        # Act
        result = await explore_children_node(state)

        # Assert
        # No URLs should be added because depth + 1 (3) > max_depth (2)
        assert len(result["pending_urls"]) == 0

    @pytest.mark.asyncio
    async def test_duplicate_urls_skipped(
        self, explore_children_node, mock_scraper, mock_link_analyzer
    ):
        """Already visited URLs should be skipped."""
        # Arrange
        mock_scraper.fetch_html.return_value = "<html>...</html>"
        mock_link_analyzer.analyze_member_list_links.return_value = [
            "https://jcp.or.jp/hokkaido",
            "https://jcp.or.jp/tokyo",
            "https://jcp.or.jp/osaka",
        ]

        state = {
            "current_url": "https://jcp.or.jp/giin/",
            "party_name": "日本共産党",
            "depth": 0,
            "max_depth": 2,
            "pending_urls": [],
            "visited_urls": {
                "https://jcp.or.jp/hokkaido",  # Already visited
                "https://jcp.or.jp/osaka",  # Already visited
            },
        }

        # Act
        result = await explore_children_node(state)

        # Assert
        # Only Tokyo should be added (Hokkaido and Osaka are already visited)
        assert len(result["pending_urls"]) == 1
        pending_urls_dict = dict(result["pending_urls"])
        assert "https://jcp.or.jp/tokyo" in pending_urls_dict
        assert "https://jcp.or.jp/hokkaido" not in pending_urls_dict
        assert "https://jcp.or.jp/osaka" not in pending_urls_dict

    @pytest.mark.asyncio
    async def test_normalized_urls_saved(
        self, explore_children_node, mock_scraper, mock_link_analyzer
    ):
        """URLs should be normalized before being saved."""
        # Arrange
        mock_scraper.fetch_html.return_value = "<html>...</html>"
        # URLs with trailing slashes and fragments
        mock_link_analyzer.analyze_member_list_links.return_value = [
            "https://jcp.or.jp/hokkaido/",  # Trailing slash
            "https://jcp.or.jp/tokyo#section",  # Fragment
        ]

        state = {
            "current_url": "https://jcp.or.jp/giin/",
            "party_name": "日本共産党",
            "depth": 0,
            "max_depth": 2,
            "pending_urls": [],
            "visited_urls": set(),
        }

        # Act
        result = await explore_children_node(state)

        # Assert
        assert len(result["pending_urls"]) == 2
        # URLs should be normalized (trailing slash and fragment removed)
        pending_urls_dict = dict(result["pending_urls"])
        # normalize_url removes trailing slashes and fragments
        assert "https://jcp.or.jp/hokkaido" in pending_urls_dict
        assert "https://jcp.or.jp/tokyo" in pending_urls_dict

    @pytest.mark.asyncio
    async def test_no_current_url_returns_unchanged_state(
        self, explore_children_node, mock_scraper, mock_link_analyzer
    ):
        """Should return state unchanged if current_url is missing."""
        # Arrange
        state = {
            "current_url": "",  # Empty URL
            "party_name": "日本共産党",
            "depth": 0,
            "max_depth": 2,
            "pending_urls": [],
            "visited_urls": set(),
        }

        # Act
        result = await explore_children_node(state)

        # Assert
        assert result == state
        # Scraper should not be called
        mock_scraper.fetch_html.assert_not_called()
        mock_link_analyzer.analyze_member_list_links.assert_not_called()

    @pytest.mark.asyncio
    async def test_no_html_content_returns_unchanged_state(
        self, explore_children_node, mock_scraper, mock_link_analyzer
    ):
        """Should return state unchanged if HTML content is empty."""
        # Arrange
        mock_scraper.fetch_html.return_value = None

        state = {
            "current_url": "https://jcp.or.jp/giin/",
            "party_name": "日本共産党",
            "depth": 0,
            "max_depth": 2,
            "pending_urls": [],
            "visited_urls": set(),
        }

        # Act
        result = await explore_children_node(state)

        # Assert
        assert result == state
        # Link analyzer should not be called
        mock_link_analyzer.analyze_member_list_links.assert_not_called()

    @pytest.mark.asyncio
    async def test_error_during_fetch_returns_unchanged_state(
        self, explore_children_node, mock_scraper, mock_link_analyzer
    ):
        """Should return state unchanged if an error occurs during fetch."""
        # Arrange
        mock_scraper.fetch_html.side_effect = Exception("Network error")

        state = {
            "current_url": "https://jcp.or.jp/giin/",
            "party_name": "日本共産党",
            "depth": 0,
            "max_depth": 2,
            "pending_urls": [],
            "visited_urls": set(),
        }

        # Act
        result = await explore_children_node(state)

        # Assert
        # State should be unchanged (graceful error handling)
        assert result == state

    @pytest.mark.asyncio
    async def test_error_during_analysis_returns_unchanged_state(
        self, explore_children_node, mock_scraper, mock_link_analyzer
    ):
        """Should return state unchanged if an error occurs during analysis."""
        # Arrange
        mock_scraper.fetch_html.return_value = "<html>...</html>"
        mock_link_analyzer.analyze_member_list_links.side_effect = Exception(
            "LLM error"
        )

        state = {
            "current_url": "https://jcp.or.jp/giin/",
            "party_name": "日本共産党",
            "depth": 0,
            "max_depth": 2,
            "pending_urls": [],
            "visited_urls": set(),
        }

        # Act
        result = await explore_children_node(state)

        # Assert
        # State should be unchanged (graceful error handling)
        assert result == state

    @pytest.mark.asyncio
    async def test_multiple_links_at_different_depths(
        self, explore_children_node, mock_scraper, mock_link_analyzer
    ):
        """Should correctly handle adding links when starting at non-zero depth."""
        # Arrange
        mock_scraper.fetch_html.return_value = "<html>...</html>"
        mock_link_analyzer.analyze_member_list_links.return_value = [
            "https://jcp.or.jp/hokkaido/sapporo",
            "https://jcp.or.jp/hokkaido/hakodate",
        ]

        state = {
            "current_url": "https://jcp.or.jp/hokkaido/",
            "party_name": "日本共産党",
            "depth": 1,  # Starting at depth 1
            "max_depth": 3,
            "pending_urls": [],
            "visited_urls": set(),
        }

        # Act
        result = await explore_children_node(state)

        # Assert
        assert len(result["pending_urls"]) == 2
        pending_urls_dict = dict(result["pending_urls"])
        # Links should be added at depth 2 (1 + 1)
        assert pending_urls_dict["https://jcp.or.jp/hokkaido/sapporo"] == 2
        assert pending_urls_dict["https://jcp.or.jp/hokkaido/hakodate"] == 2

    @pytest.mark.asyncio
    async def test_preserves_existing_pending_urls(
        self, explore_children_node, mock_scraper, mock_link_analyzer
    ):
        """Should preserve existing pending_urls when adding new ones."""
        # Arrange
        mock_scraper.fetch_html.return_value = "<html>...</html>"
        mock_link_analyzer.analyze_member_list_links.return_value = [
            "https://jcp.or.jp/osaka",
        ]

        state = {
            "current_url": "https://jcp.or.jp/giin/",
            "party_name": "日本共産党",
            "depth": 0,
            "max_depth": 2,
            "pending_urls": [
                ("https://jcp.or.jp/hokkaido", 1),
                ("https://jcp.or.jp/tokyo", 1),
            ],
            "visited_urls": set(),
        }

        # Act
        result = await explore_children_node(state)

        # Assert
        assert len(result["pending_urls"]) == 3
        pending_urls_dict = dict(result["pending_urls"])
        # Existing URLs should be preserved
        assert "https://jcp.or.jp/hokkaido" in pending_urls_dict
        assert "https://jcp.or.jp/tokyo" in pending_urls_dict
        # New URL should be added
        assert "https://jcp.or.jp/osaka" in pending_urls_dict
