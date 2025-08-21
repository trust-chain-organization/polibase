"""Tests for pagination models and utilities."""

import pytest

from src.domain.pagination import PaginatedResult, PaginationParams


class TestPaginationParams:
    """Test cases for PaginationParams."""

    def test_initialization_with_defaults(self) -> None:
        """Test initialization with default values."""
        params = PaginationParams()

        assert params.page == 1
        assert params.per_page == 50

    def test_initialization_with_custom_values(self) -> None:
        """Test initialization with custom values."""
        params = PaginationParams(page=3, per_page=20)

        assert params.page == 3
        assert params.per_page == 20

    def test_offset_calculation(self) -> None:
        """Test offset calculation for database queries."""
        # First page
        params1 = PaginationParams(page=1, per_page=10)
        assert params1.offset == 0

        # Second page
        params2 = PaginationParams(page=2, per_page=10)
        assert params2.offset == 10

        # Third page with different per_page
        params3 = PaginationParams(page=3, per_page=25)
        assert params3.offset == 50

    def test_limit_property(self) -> None:
        """Test limit property returns per_page value."""
        params = PaginationParams(page=1, per_page=30)
        assert params.limit == 30

    def test_validate_valid_params(self) -> None:
        """Test validation with valid parameters."""
        valid_params = [
            PaginationParams(page=1, per_page=1),
            PaginationParams(page=100, per_page=50),
            PaginationParams(page=1, per_page=100),
        ]

        for params in valid_params:
            params.validate()  # Should not raise

    def test_validate_invalid_page(self) -> None:
        """Test validation with invalid page number."""
        params = PaginationParams(page=0, per_page=10)

        with pytest.raises(ValueError, match="Page must be >= 1"):
            params.validate()

        params2 = PaginationParams(page=-1, per_page=10)

        with pytest.raises(ValueError, match="Page must be >= 1"):
            params2.validate()

    def test_validate_invalid_per_page_too_small(self) -> None:
        """Test validation with per_page too small."""
        params = PaginationParams(page=1, per_page=0)

        with pytest.raises(ValueError, match="Per page must be >= 1"):
            params.validate()

        params2 = PaginationParams(page=1, per_page=-5)

        with pytest.raises(ValueError, match="Per page must be >= 1"):
            params2.validate()

    def test_validate_invalid_per_page_too_large(self) -> None:
        """Test validation with per_page too large."""
        params = PaginationParams(page=1, per_page=101)

        with pytest.raises(ValueError, match="Per page must be <= 100"):
            params.validate()

        params2 = PaginationParams(page=1, per_page=200)

        with pytest.raises(ValueError, match="Per page must be <= 100"):
            params2.validate()


class TestPaginatedResult:
    """Test cases for PaginatedResult."""

    def test_initialization(self) -> None:
        """Test PaginatedResult initialization."""
        items = ["item1", "item2", "item3"]
        result = PaginatedResult(items=items, total_count=10, page=1, per_page=3)

        assert result.items == items
        assert result.total_count == 10
        assert result.page == 1
        assert result.per_page == 3

    def test_total_pages_calculation(self) -> None:
        """Test total pages calculation."""
        # Exact division
        result1 = PaginatedResult(items=[], total_count=20, page=1, per_page=10)
        assert result1.total_pages == 2

        # With remainder
        result2 = PaginatedResult(items=[], total_count=25, page=1, per_page=10)
        assert result2.total_pages == 3

        # Single item
        result3 = PaginatedResult(items=[], total_count=1, page=1, per_page=10)
        assert result3.total_pages == 1

        # Empty result
        result4 = PaginatedResult(items=[], total_count=0, page=1, per_page=10)
        assert result4.total_pages == 0

    def test_has_next_property(self) -> None:
        """Test has_next property."""
        # Has next page
        result1 = PaginatedResult(items=[], total_count=30, page=1, per_page=10)
        assert result1.has_next is True

        # On last page
        result2 = PaginatedResult(items=[], total_count=30, page=3, per_page=10)
        assert result2.has_next is False

        # Single page
        result3 = PaginatedResult(items=[], total_count=5, page=1, per_page=10)
        assert result3.has_next is False

    def test_has_previous_property(self) -> None:
        """Test has_previous property."""
        # First page
        result1 = PaginatedResult(items=[], total_count=30, page=1, per_page=10)
        assert result1.has_previous is False

        # Second page
        result2 = PaginatedResult(items=[], total_count=30, page=2, per_page=10)
        assert result2.has_previous is True

        # Last page
        result3 = PaginatedResult(items=[], total_count=30, page=3, per_page=10)
        assert result3.has_previous is True

    def test_next_page_property(self) -> None:
        """Test next_page property."""
        # Has next page
        result1 = PaginatedResult(items=[], total_count=30, page=2, per_page=10)
        assert result1.next_page == 3

        # No next page
        result2 = PaginatedResult(items=[], total_count=30, page=3, per_page=10)
        assert result2.next_page is None

    def test_previous_page_property(self) -> None:
        """Test previous_page property."""
        # Has previous page
        result1 = PaginatedResult(items=[], total_count=30, page=2, per_page=10)
        assert result1.previous_page == 1

        # No previous page
        result2 = PaginatedResult(items=[], total_count=30, page=1, per_page=10)
        assert result2.previous_page is None

    def test_to_dict(self) -> None:
        """Test conversion to dictionary."""
        items = [{"id": 1, "name": "Item 1"}, {"id": 2, "name": "Item 2"}]
        result = PaginatedResult(items=items, total_count=5, page=2, per_page=2)

        dict_result = result.to_dict()

        assert dict_result["items"] == items
        assert dict_result["pagination"]["total_count"] == 5
        assert dict_result["pagination"]["total_pages"] == 3
        assert dict_result["pagination"]["current_page"] == 2
        assert dict_result["pagination"]["per_page"] == 2
        assert dict_result["pagination"]["has_next"] is True
        assert dict_result["pagination"]["has_previous"] is True
        assert dict_result["pagination"]["next_page"] == 3
        assert dict_result["pagination"]["previous_page"] == 1

    def test_edge_case_empty_result(self) -> None:
        """Test edge case with empty result."""
        result = PaginatedResult(items=[], total_count=0, page=1, per_page=10)

        assert result.total_pages == 0
        assert result.has_next is False
        assert result.has_previous is False
        assert result.next_page is None
        assert result.previous_page is None

        dict_result = result.to_dict()
        assert dict_result["items"] == []
        assert dict_result["pagination"]["total_count"] == 0
        assert dict_result["pagination"]["total_pages"] == 0

    def test_type_generic(self) -> None:
        """Test that PaginatedResult works with different types."""
        # With strings
        string_result = PaginatedResult[str](
            items=["a", "b", "c"], total_count=3, page=1, per_page=10
        )
        assert isinstance(string_result.items[0], str)

        # With dictionaries
        dict_result = PaginatedResult[dict](
            items=[{"key": "value"}], total_count=1, page=1, per_page=10
        )
        assert isinstance(dict_result.items[0], dict)

        # With custom objects
        class CustomObject:
            def __init__(self, value: int) -> None:
                self.value = value

        obj_result = PaginatedResult[CustomObject](
            items=[CustomObject(1), CustomObject(2)], total_count=2, page=1, per_page=10
        )
        assert isinstance(obj_result.items[0], CustomObject)

    def test_middle_page_navigation(self) -> None:
        """Test navigation properties for a middle page."""
        result = PaginatedResult(
            items=["item1", "item2"], total_count=10, page=3, per_page=2
        )

        assert result.total_pages == 5
        assert result.has_next is True
        assert result.has_previous is True
        assert result.next_page == 4
        assert result.previous_page == 2
