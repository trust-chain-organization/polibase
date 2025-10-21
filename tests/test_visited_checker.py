"""Unit tests for visited URL checker node."""

import pytest

from src.infrastructure.external.langgraph_nodes.visited_checker_node import (
    add_pending_url_with_checks,
    check_visited_and_depth,
)


def create_test_state(**overrides):
    """Helper to create a complete LangGraph state for testing."""
    state = {
        "current_url": "https://example.com/page",
        "visited_urls": set(),
        "depth": 1,
        "max_depth": 3,
        "messages": [],
        "party_name": "Test Party",
        "party_id": 1,
        "pending_urls": [],
        "extracted_members": [],
        "error_message": None,
    }
    state.update(overrides)
    return state


class TestCheckVisitedAndDepth:
    """Test cases for check_visited_and_depth node function."""

    def test_new_url_within_depth_limit(self) -> None:
        """Test processing a new URL within depth limit."""
        state = {
            "current_url": "https://example.com/page1",
            "visited_urls": set(),
            "depth": 1,
            "max_depth": 3,
            "messages": [],
            "party_name": "Test Party",
            "party_id": 1,
            "pending_urls": [],
            "extracted_members": [],
            "error_message": None,
        }

        result = check_visited_and_depth(state)

        assert not result["should_skip"]
        assert result["skip_reason"] is None
        assert "https://example.com/page1" in result["visited_urls"]
        assert len(result["messages"]) > 0

    def test_already_visited_url(self) -> None:
        """Test skipping already visited URL (infinite loop prevention)."""
        visited_url = "https://example.com/page1"
        state = {
            "current_url": visited_url,
            "visited_urls": {visited_url},
            "depth": 1,
            "max_depth": 3,
            "messages": [],
            "party_name": "Test Party",
            "party_id": 1,
            "pending_urls": [],
            "extracted_members": [],
            "error_message": None,
        }

        result = check_visited_and_depth(state)

        assert result["should_skip"]
        assert result["skip_reason"] == "already_visited"
        # Should not add duplicate
        assert len(result["visited_urls"]) == 1

    def test_depth_limit_exceeded(self) -> None:
        """Test skipping URL when depth limit is exceeded."""
        state = {
            "current_url": "https://example.com/deep/page",
            "visited_urls": set(),
            "depth": 4,
            "max_depth": 3,
            "messages": [],
            "party_name": "Test Party",
            "party_id": 1,
            "pending_urls": [],
            "extracted_members": [],
            "error_message": None,
        }

        result = check_visited_and_depth(state)

        assert result["should_skip"]
        assert result["skip_reason"] == "max_depth_exceeded"
        # Should not add to visited_urls
        assert len(result["visited_urls"]) == 0

    def test_depth_at_max_allowed(self) -> None:
        """Test processing URL when depth equals max_depth."""
        state = {
            "current_url": "https://example.com/page",
            "visited_urls": set(),
            "depth": 3,
            "max_depth": 3,
            "messages": [],
            "party_name": "Test Party",
            "party_id": 1,
            "pending_urls": [],
            "extracted_members": [],
            "error_message": None,
        }

        result = check_visited_and_depth(state)

        # At max depth should still be processed (not exceeded)
        assert not result["should_skip"]
        assert "https://example.com/page" in result["visited_urls"]

    def test_invalid_url(self) -> None:
        """Test handling of invalid URL."""
        state = {
            "current_url": "not-a-valid-url",
            "visited_urls": set(),
            "depth": 1,
            "max_depth": 3,
            "messages": [],
            "party_name": "Test Party",
            "party_id": 1,
            "pending_urls": [],
            "extracted_members": [],
            "error_message": None,
        }

        result = check_visited_and_depth(state)

        assert result["should_skip"]
        assert result["skip_reason"] == "invalid_url"
        assert len(result["visited_urls"]) == 0

    def test_url_normalization_consistency(self) -> None:
        """Test that URL normalization prevents duplicate visits."""
        state = {
            "current_url": "HTTPS://Example.COM/path/",
            "visited_urls": {"https://example.com/path"},
            "depth": 1,
            "max_depth": 3,
            "messages": [],
            "party_name": "Test Party",
            "party_id": 1,
            "pending_urls": [],
            "extracted_members": [],
            "error_message": None,
        }

        result = check_visited_and_depth(state)

        # Should be recognized as already visited due to normalization
        # (scheme and host are normalized, trailing slash removed)
        assert result["should_skip"]
        assert result["skip_reason"] == "already_visited"

    def test_messages_added_to_state(self) -> None:
        """Test that status messages are added to state."""
        state = {
            "current_url": "https://example.com/page",
            "visited_urls": set(),
            "depth": 1,
            "max_depth": 3,
            "messages": [],
            "party_name": "Test Party",
            "party_id": 1,
            "pending_urls": [],
            "extracted_members": [],
            "error_message": None,
        }

        result = check_visited_and_depth(state)

        assert len(result["messages"]) > 0
        # Should have a message indicating processing
        message_content = result["messages"][0].content
        assert "example.com/page" in message_content

    def test_missing_state_fields_use_defaults(self) -> None:
        """Test that missing state fields use sensible defaults."""
        state = {
            "depth": 1,
            "current_url": "https://example.com/page",
            "party_name": "Test Party",
            "party_id": 1,
            "pending_urls": [],
            "extracted_members": [],
            "error_message": None,
            "max_depth": 3,
        }

        result = check_visited_and_depth(state)

        # Should not raise error and should process with defaults
        assert "visited_urls" in result
        assert "messages" in result
        assert not result["should_skip"]

    def test_state_immutability(self) -> None:
        """Test that original state is not mutated."""
        original_visited = {"https://example.com/old"}
        state = {
            "current_url": "https://example.com/new",
            "visited_urls": original_visited.copy(),
            "depth": 1,
            "max_depth": 3,
            "messages": [],
            "party_name": "Test Party",
            "party_id": 1,
            "pending_urls": [],
            "extracted_members": [],
            "error_message": None,
        }

        result = check_visited_and_depth(state)

        # Original visited set should remain unchanged
        assert len(original_visited) == 1
        assert "https://example.com/old" in original_visited
        # Result should have both
        assert len(result["visited_urls"]) == 2


class TestAddPendingUrlWithChecks:
    """Test cases for add_pending_url_with_checks helper function."""

    def test_add_new_url_within_depth(self) -> None:
        """Test adding a new URL within depth limit."""
        state = {
            "current_url": "https://example.com/page",
            "depth": 1,
            "visited_urls": set(),
            "pending_urls": [],
            "max_depth": 3,
            "messages": [],
            "party_name": "Test Party",
            "party_id": 1,
            "extracted_members": [],
            "error_message": None,
        }

        result = add_pending_url_with_checks(state, "https://example.com/page", 1)

        assert len(result["pending_urls"]) == 1
        url, depth = result["pending_urls"][0]
        assert url == "https://example.com/page"
        assert depth == 1

    def test_skip_already_visited_url(self) -> None:
        """Test that already visited URLs are not added to queue."""
        state = {
            "current_url": "https://example.com/page",
            "depth": 1,
            "visited_urls": {"https://example.com/page"},
            "pending_urls": [],
            "max_depth": 3,
            "messages": [],
            "party_name": "Test Party",
            "party_id": 1,
            "extracted_members": [],
            "error_message": None,
        }

        result = add_pending_url_with_checks(state, "https://example.com/page", 1)

        # Should not add to pending
        assert len(result["pending_urls"]) == 0

    def test_skip_url_beyond_max_depth(self) -> None:
        """Test that URLs beyond max depth are not added."""
        state = {
            "current_url": "https://example.com/page",
            "depth": 1,
            "visited_urls": set(),
            "pending_urls": [],
            "max_depth": 3,
            "messages": [],
            "party_name": "Test Party",
            "party_id": 1,
            "extracted_members": [],
            "error_message": None,
        }

        result = add_pending_url_with_checks(state, "https://example.com/deep", 4)

        # Should not add to pending
        assert len(result["pending_urls"]) == 0

    def test_url_at_max_depth_is_added(self) -> None:
        """Test that URLs at max depth are still added."""
        state = {
            "current_url": "https://example.com/page",
            "depth": 1,
            "visited_urls": set(),
            "pending_urls": [],
            "max_depth": 3,
            "messages": [],
            "party_name": "Test Party",
            "party_id": 1,
            "extracted_members": [],
            "error_message": None,
        }

        result = add_pending_url_with_checks(state, "https://example.com/page", 3)

        # Should be added (at max depth, not beyond)
        assert len(result["pending_urls"]) == 1

    def test_negative_depth_raises_error(self) -> None:
        """Test that negative depth raises ValueError."""
        state = {
            "current_url": "https://example.com/page",
            "depth": 1,
            "visited_urls": set(),
            "pending_urls": [],
            "max_depth": 3,
            "messages": [],
            "party_name": "Test Party",
            "party_id": 1,
            "extracted_members": [],
            "error_message": None,
        }

        with pytest.raises(ValueError, match="Depth cannot be negative"):
            add_pending_url_with_checks(state, "https://example.com/page", -1)

    def test_invalid_url_handled_gracefully(self) -> None:
        """Test that invalid URLs are handled without crashing."""
        state = {
            "current_url": "https://example.com/page",
            "depth": 1,
            "visited_urls": set(),
            "pending_urls": [],
            "max_depth": 3,
            "messages": [],
            "party_name": "Test Party",
            "party_id": 1,
            "extracted_members": [],
            "error_message": None,
        }

        result = add_pending_url_with_checks(state, "invalid-url", 1)

        # Should not add to pending but should handle gracefully
        assert len(result["pending_urls"]) == 0
        # Should have error message
        assert len(result["messages"]) > 0

    def test_url_normalization_prevents_duplicates(self) -> None:
        """Test that URL normalization prevents duplicate pending URLs."""
        # Test that visited_urls check prevents duplicates via normalization
        state_with_visited = {
            "current_url": "https://example.com/page",
            "depth": 1,
            "visited_urls": {"https://example.com/page"},
            "max_depth": 3,
            "messages": [],
            "party_name": "Test Party",
            "party_id": 1,
            "pending_urls": [],
            "extracted_members": [],
            "error_message": None,
        }

        # Add same URL with different case/trailing slash (lowercase path to match)
        result = add_pending_url_with_checks(
            state_with_visited, "HTTPS://Example.COM/page/", 1
        )

        # Should not be added because normalized URL is already visited
        assert len(result["pending_urls"]) == 0

    def test_multiple_urls_added(self) -> None:
        """Test adding multiple URLs sequentially."""
        state = {
            "current_url": "https://example.com/page",
            "depth": 1,
            "visited_urls": set(),
            "pending_urls": [],
            "max_depth": 3,
            "messages": [],
            "party_name": "Test Party",
            "party_id": 1,
            "extracted_members": [],
            "error_message": None,
        }

        # Add first URL
        state = add_pending_url_with_checks(state, "https://example.com/page1", 1)
        # Add second URL
        state = add_pending_url_with_checks(state, "https://example.com/page2", 1)
        # Add third URL
        state = add_pending_url_with_checks(state, "https://example.com/page3", 2)

        assert len(state["pending_urls"]) == 3
        # Check that depths are preserved
        depths = [depth for _, depth in state["pending_urls"]]
        assert depths == [1, 1, 2]

    def test_messages_added_on_success(self) -> None:
        """Test that success messages are added to state."""
        state = {
            "current_url": "https://example.com/page",
            "depth": 1,
            "visited_urls": set(),
            "pending_urls": [],
            "max_depth": 3,
            "messages": [],
            "party_name": "Test Party",
            "party_id": 1,
            "extracted_members": [],
            "error_message": None,
        }

        result = add_pending_url_with_checks(state, "https://example.com/page", 1)

        assert len(result["messages"]) > 0
        message_content = result["messages"][0].content
        assert "example.com/page" in message_content


class TestVisitedCheckerIntegration:
    """Integration tests combining both functions."""

    def test_check_then_add_child_urls(self) -> None:
        """Test typical workflow: check current URL, then add child URLs."""
        # Initialize state
        state = {
            "current_url": "https://example.com/parent",
            "visited_urls": set(),
            "pending_urls": [],
            "depth": 1,
            "max_depth": 3,
            "messages": [],
            "party_name": "Test Party",
            "party_id": 1,
            "extracted_members": [],
            "error_message": None,
        }

        # Check and mark current URL as visited
        state = check_visited_and_depth(state)
        assert not state["should_skip"]
        assert "https://example.com/parent" in state["visited_urls"]

        # Add child URLs
        state = add_pending_url_with_checks(state, "https://example.com/child1", 2)
        state = add_pending_url_with_checks(state, "https://example.com/child2", 2)

        assert len(state["pending_urls"]) == 2

    def test_prevent_circular_references(self) -> None:
        """Test that circular page references are prevented."""
        state = {
            "current_url": "https://example.com/page1",
            "visited_urls": set(),
            "pending_urls": [],
            "depth": 1,
            "max_depth": 3,
            "messages": [],
            "party_name": "Test Party",
            "party_id": 1,
            "extracted_members": [],
            "error_message": None,
        }

        # Visit page1
        state = check_visited_and_depth(state)

        # Try to add page1 as child (circular reference)
        state = add_pending_url_with_checks(state, "https://example.com/page1", 2)

        # Should not be added to pending (already visited)
        assert len(state["pending_urls"]) == 0
