"""Tests for decision node logic."""

from src.infrastructure.external.langgraph_nodes.decision_node import (
    should_explore_children,
)


class TestDecisionNode:
    """Test decision node for navigation strategy."""

    def test_explore_children_for_index_page_confident(self):
        """Test that confident index pages trigger explore_children."""
        state = {
            "classification": {
                "page_type": "index_page",
                "confidence": 0.9,
            },
            "depth": 1,
            "max_depth": 3,
            "pending_urls": [],
        }

        result = should_explore_children(state)  # type: ignore[arg-type]
        assert result == "explore_children"

    def test_extract_members_for_member_list_page_confident(self):
        """Test that confident member list pages trigger extract_members."""
        state = {
            "classification": {
                "page_type": "member_list_page",
                "confidence": 0.95,
            },
            "depth": 1,
            "max_depth": 3,
            "pending_urls": [],
        }

        result = should_explore_children(state)  # type: ignore[arg-type]
        assert result == "extract_members"

    def test_skip_other_pages(self):
        """Test that OTHER pages are skipped when pending URLs exist."""
        state = {
            "classification": {
                "page_type": "other",
                "confidence": 0.8,
            },
            "depth": 1,
            "max_depth": 3,
            "pending_urls": [("https://example.com/next", 1)],
        }

        result = should_explore_children(state)  # type: ignore[arg-type]
        assert result == "continue"

    def test_end_when_no_pending_urls(self):
        """Test that END is returned when no pending URLs remain."""
        state = {
            "classification": {
                "page_type": "other",
                "confidence": 0.8,
            },
            "depth": 1,
            "max_depth": 3,
            "pending_urls": [],
        }

        result = should_explore_children(state)  # type: ignore[arg-type]
        assert result == "end"

    def test_skip_when_max_depth_reached(self):
        """Test that navigation stops when max depth is reached."""
        state = {
            "classification": {
                "page_type": "index_page",
                "confidence": 0.9,
            },
            "depth": 3,
            "max_depth": 3,
            "pending_urls": [("https://example.com/next", 3)],
        }

        result = should_explore_children(state)  # type: ignore[arg-type]
        assert result == "continue"  # Should skip and continue to next URL

    def test_skip_low_confidence_index_page(self):
        """Test that low confidence index pages are skipped."""
        state = {
            "classification": {
                "page_type": "index_page",
                "confidence": 0.5,
            },
            "depth": 1,
            "max_depth": 3,
            "pending_urls": [("https://example.com/next", 1)],
        }

        result = should_explore_children(state)  # type: ignore[arg-type]
        assert result == "continue"

    def test_skip_low_confidence_member_list_page(self):
        """Test that low confidence member list pages are skipped."""
        state = {
            "classification": {
                "page_type": "member_list_page",
                "confidence": 0.6,
            },
            "depth": 1,
            "max_depth": 3,
            "pending_urls": [],
        }

        result = should_explore_children(state)  # type: ignore[arg-type]
        assert result == "end"

    def test_handles_missing_classification(self):
        """Test that missing classification is handled gracefully."""
        state = {
            "depth": 1,
            "max_depth": 3,
            "pending_urls": [("https://example.com/next", 1)],
        }

        result = should_explore_children(state)  # type: ignore[arg-type]
        assert result == "continue"  # Should treat as "other" and continue

    def test_handles_invalid_page_type(self):
        """Test that invalid page_type is handled gracefully."""
        state = {
            "classification": {
                "page_type": "invalid_type",
                "confidence": 0.9,
            },
            "depth": 1,
            "max_depth": 3,
            "pending_urls": [],
        }

        result = should_explore_children(state)  # type: ignore[arg-type]
        assert result == "end"  # Should treat as unknown and end

    def test_depth_zero_with_index_page(self):
        """Test that depth 0 (root page) works correctly."""
        state = {
            "classification": {
                "page_type": "index_page",
                "confidence": 0.9,
            },
            "depth": 0,
            "max_depth": 2,
            "pending_urls": [],
        }

        result = should_explore_children(state)  # type: ignore[arg-type]
        assert result == "explore_children"

    def test_boundary_depth_equal_to_max(self):
        """Test boundary condition when depth equals max_depth."""
        state = {
            "classification": {
                "page_type": "index_page",
                "confidence": 0.9,
            },
            "depth": 2,
            "max_depth": 2,
            "pending_urls": [("https://example.com/next", 2)],
        }

        result = should_explore_children(state)  # type: ignore[arg-type]
        # Should not explore deeper, but should continue to next URL
        assert result == "continue"

    def test_confidence_exactly_at_threshold(self):
        """Test classification with confidence exactly at 0.7 threshold."""
        state = {
            "classification": {
                "page_type": "index_page",
                "confidence": 0.7,
            },
            "depth": 1,
            "max_depth": 3,
            "pending_urls": [],
        }

        result = should_explore_children(state)  # type: ignore[arg-type]
        assert result == "explore_children"  # 0.7 should be accepted (>=)
