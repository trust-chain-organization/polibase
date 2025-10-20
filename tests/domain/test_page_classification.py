"""Tests for PageClassification value object."""

import pytest

from src.domain.value_objects.page_classification import PageClassification, PageType


class TestPageType:
    """Test PageType enum."""

    def test_page_type_values(self):
        """Test PageType enum values."""
        assert PageType.INDEX_PAGE.value == "index_page"
        assert PageType.MEMBER_LIST_PAGE.value == "member_list_page"
        assert PageType.OTHER.value == "other"


class TestPageClassification:
    """Test PageClassification value object."""

    def test_create_valid_classification(self):
        """Test creating a valid PageClassification."""
        classification = PageClassification(
            page_type=PageType.INDEX_PAGE,
            confidence=0.9,
            reason="Page contains many regional links",
            has_child_links=True,
            has_member_info=False,
        )

        assert classification.page_type == PageType.INDEX_PAGE
        assert classification.confidence == 0.9
        assert classification.reason == "Page contains many regional links"
        assert classification.has_child_links is True
        assert classification.has_member_info is False

    def test_invalid_confidence_above_one(self):
        """Test that confidence above 1.0 raises ValueError."""
        with pytest.raises(ValueError, match="Confidence must be between 0.0 and 1.0"):
            PageClassification(
                page_type=PageType.INDEX_PAGE,
                confidence=1.5,
                reason="Test",
                has_child_links=True,
                has_member_info=False,
            )

    def test_invalid_confidence_below_zero(self):
        """Test that confidence below 0.0 raises ValueError."""
        with pytest.raises(ValueError, match="Confidence must be between 0.0 and 1.0"):
            PageClassification(
                page_type=PageType.OTHER,
                confidence=-0.1,
                reason="Test",
                has_child_links=False,
                has_member_info=False,
            )

    def test_is_confident_with_default_threshold(self):
        """Test is_confident with default threshold (0.7)."""
        high_confidence = PageClassification(
            page_type=PageType.MEMBER_LIST_PAGE,
            confidence=0.8,
            reason="High confidence",
            has_child_links=False,
            has_member_info=True,
        )
        assert high_confidence.is_confident() is True

        low_confidence = PageClassification(
            page_type=PageType.OTHER,
            confidence=0.6,
            reason="Low confidence",
            has_child_links=False,
            has_member_info=False,
        )
        assert low_confidence.is_confident() is False

    def test_is_confident_with_custom_threshold(self):
        """Test is_confident with custom threshold."""
        classification = PageClassification(
            page_type=PageType.INDEX_PAGE,
            confidence=0.75,
            reason="Medium confidence",
            has_child_links=True,
            has_member_info=False,
        )

        assert classification.is_confident(threshold=0.7) is True
        assert classification.is_confident(threshold=0.8) is False

    def test_should_explore_children_index_page_confident(self):
        """Test should_explore_children for confident index page."""
        classification = PageClassification(
            page_type=PageType.INDEX_PAGE,
            confidence=0.9,
            reason="Clear index page",
            has_child_links=True,
            has_member_info=False,
        )

        assert classification.should_explore_children(max_depth_reached=False) is True
        assert classification.should_explore_children(max_depth_reached=True) is False

    def test_should_explore_children_index_page_not_confident(self):
        """Test should_explore_children for non-confident index page."""
        classification = PageClassification(
            page_type=PageType.INDEX_PAGE,
            confidence=0.5,
            reason="Uncertain classification",
            has_child_links=True,
            has_member_info=False,
        )

        assert classification.should_explore_children(max_depth_reached=False) is False

    def test_should_explore_children_member_list_page(self):
        """Test should_explore_children for member list page."""
        classification = PageClassification(
            page_type=PageType.MEMBER_LIST_PAGE,
            confidence=0.95,
            reason="Contains member information",
            has_child_links=False,
            has_member_info=True,
        )

        assert classification.should_explore_children(max_depth_reached=False) is False

    def test_should_extract_members_member_list_page_confident(self):
        """Test should_extract_members for confident member list page."""
        classification = PageClassification(
            page_type=PageType.MEMBER_LIST_PAGE,
            confidence=0.9,
            reason="Multiple member profiles found",
            has_child_links=False,
            has_member_info=True,
        )

        assert classification.should_extract_members() is True

    def test_should_extract_members_member_list_page_not_confident(self):
        """Test should_extract_members for non-confident member list page."""
        classification = PageClassification(
            page_type=PageType.MEMBER_LIST_PAGE,
            confidence=0.6,
            reason="Possible member list",
            has_child_links=False,
            has_member_info=True,
        )

        assert classification.should_extract_members() is False

    def test_should_extract_members_index_page(self):
        """Test should_extract_members for index page."""
        classification = PageClassification(
            page_type=PageType.INDEX_PAGE,
            confidence=0.9,
            reason="Index page",
            has_child_links=True,
            has_member_info=False,
        )

        assert classification.should_extract_members() is False

    def test_frozen_dataclass(self):
        """Test that PageClassification is frozen (immutable)."""
        classification = PageClassification(
            page_type=PageType.OTHER,
            confidence=0.5,
            reason="Test",
            has_child_links=False,
            has_member_info=False,
        )

        with pytest.raises(AttributeError):
            classification.confidence = 0.8  # type: ignore[misc]
