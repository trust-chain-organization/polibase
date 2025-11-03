"""Unit tests for PartyScrapingState domain entity."""

from collections import deque

import pytest

from src.domain.entities.party_scraping_state import PartyScrapingState
from src.domain.value_objects.politician_member_data import PoliticianMemberData


class TestPartyScrapingStateCreation:
    """Tests for PartyScrapingState creation."""

    def test_creation_with_required_fields(self):
        """Test creating a state with only required fields."""
        state = PartyScrapingState(
            current_url="https://example.com",
            party_name="Test Party",
            party_id=1,
            max_depth=3,
        )

        assert state.current_url == "https://example.com"
        assert state.party_name == "Test Party"
        assert state.party_id == 1
        assert state.max_depth == 3
        assert len(state.visited_urls) == 0
        assert len(state.pending_urls) == 0
        assert len(state.extracted_members) == 0
        assert state.depth == 0
        assert state.error_message is None


class TestImmutability:
    """Tests for immutability of state collections."""

    def test_visited_urls_returns_frozenset(self):
        """Test that visited_urls returns immutable frozenset."""
        state = PartyScrapingState(
            current_url="https://example.com",
            party_name="Test Party",
            party_id=1,
            max_depth=3,
        )

        assert isinstance(state.visited_urls, frozenset)

    def test_pending_urls_returns_tuple(self):
        """Test that pending_urls returns immutable tuple."""
        state = PartyScrapingState(
            current_url="https://example.com",
            party_name="Test Party",
            party_id=1,
            max_depth=3,
        )

        assert isinstance(state.pending_urls, tuple)

    def test_extracted_members_returns_tuple(self):
        """Test that extracted_members returns immutable tuple."""
        state = PartyScrapingState(
            current_url="https://example.com",
            party_name="Test Party",
            party_id=1,
            max_depth=3,
        )

        assert isinstance(state.extracted_members, tuple)

    def test_cannot_modify_visited_urls(self):
        """Test that external code cannot modify visited_urls."""
        state = PartyScrapingState(
            current_url="https://example.com",
            party_name="Test Party",
            party_id=1,
            max_depth=3,
        )

        # frozenset doesn't have add/remove methods
        with pytest.raises(AttributeError):
            state.visited_urls.add("https://example.com/hack")  # type: ignore[attr-defined]

    def test_cannot_modify_pending_urls(self):
        """Test that external code cannot modify pending_urls."""
        state = PartyScrapingState(
            current_url="https://example.com",
            party_name="Test Party",
            party_id=1,
            max_depth=3,
        )

        # tuple doesn't have append method
        with pytest.raises(AttributeError):
            state.pending_urls.append(("https://example.com/hack", 1))  # type: ignore[attr-defined]

    def test_cannot_modify_extracted_members(self):
        """Test that external code cannot modify extracted_members."""
        state = PartyScrapingState(
            current_url="https://example.com",
            party_name="Test Party",
            party_id=1,
            max_depth=3,
        )

        # tuple doesn't have append method
        with pytest.raises(AttributeError):
            state.extracted_members.append({"name": "Hacker"})  # type: ignore[attr-defined]

    def test_member_deep_copy_prevents_mutation(self):
        """Test that deep copying members prevents external mutation."""
        state = PartyScrapingState(
            current_url="https://example.com",
            party_name="Test Party",
            party_id=1,
            max_depth=3,
        )

        original_member: PoliticianMemberData = {
            "name": "John Doe",
            "position": "Senator",
        }
        state.add_extracted_member(original_member)

        # Mutating original should not affect stored member
        original_member["position"] = "Governor"

        assert state.extracted_members[0].get("position") == "Senator"


class TestURLNormalization:
    """Tests for URL normalization."""

    def test_normalize_url_lowercase_scheme(self):
        """Test that URL scheme is normalized to lowercase."""
        state = PartyScrapingState(
            current_url="https://example.com",
            party_name="Test Party",
            party_id=1,
            max_depth=3,
        )

        state.mark_visited("HTTPS://EXAMPLE.COM/page")

        assert state.has_visited("https://example.com/page")

    def test_normalize_url_lowercase_netloc(self):
        """Test that URL netloc is normalized to lowercase."""
        state = PartyScrapingState(
            current_url="https://example.com",
            party_name="Test Party",
            party_id=1,
            max_depth=3,
        )

        state.mark_visited("https://EXAMPLE.COM/page")

        assert state.has_visited("https://example.com/page")

    def test_normalize_url_remove_trailing_slash(self):
        """Test that trailing slash is removed (except for root)."""
        state = PartyScrapingState(
            current_url="https://example.com",
            party_name="Test Party",
            party_id=1,
            max_depth=3,
        )

        state.mark_visited("https://example.com/page/")

        assert state.has_visited("https://example.com/page")

    def test_normalize_url_keep_root_slash(self):
        """Test that root path keeps its slash."""
        state = PartyScrapingState(
            current_url="https://example.com",
            party_name="Test Party",
            party_id=1,
            max_depth=3,
        )

        state.mark_visited("https://example.com/")

        assert state.has_visited("https://example.com/")

    def test_normalize_url_remove_fragment(self):
        """Test that URL fragments are removed."""
        state = PartyScrapingState(
            current_url="https://example.com",
            party_name="Test Party",
            party_id=1,
            max_depth=3,
        )

        state.mark_visited("https://example.com/page#section")

        # Both should be treated as the same URL (fragment removed)
        assert state.has_visited("https://example.com/page")
        assert state.has_visited("https://example.com/page#section")
        assert state.has_visited("https://example.com/page#different")

    def test_normalize_url_empty_raises_error(self):
        """Test that empty URL raises ValueError."""
        state = PartyScrapingState(
            current_url="https://example.com",
            party_name="Test Party",
            party_id=1,
            max_depth=3,
        )

        with pytest.raises(ValueError, match="URL cannot be empty"):
            state.mark_visited("")

    def test_normalize_url_whitespace_only_raises_error(self):
        """Test that whitespace-only URL raises ValueError."""
        state = PartyScrapingState(
            current_url="https://example.com",
            party_name="Test Party",
            party_id=1,
            max_depth=3,
        )

        with pytest.raises(ValueError, match="URL cannot be empty"):
            state.mark_visited("   ")

    def test_normalize_url_invalid_format_raises_error(self):
        """Test that invalid URL format raises ValueError."""
        state = PartyScrapingState(
            current_url="https://example.com",
            party_name="Test Party",
            party_id=1,
            max_depth=3,
        )

        with pytest.raises(ValueError, match="Invalid URL format"):
            state.mark_visited("not-a-valid-url")

    def test_normalize_url_strips_whitespace(self):
        """Test that URL whitespace is stripped."""
        state = PartyScrapingState(
            current_url="https://example.com",
            party_name="Test Party",
            party_id=1,
            max_depth=3,
        )

        state.mark_visited("  https://example.com/page  ")

        assert state.has_visited("https://example.com/page")


class TestMemberDeduplication:
    """Tests for member deduplication."""

    def test_add_duplicate_member_returns_false(self):
        """Test that adding duplicate member returns False."""
        state = PartyScrapingState(
            current_url="https://example.com",
            party_name="Test Party",
            party_id=1,
            max_depth=3,
        )

        member: PoliticianMemberData = {"name": "John Doe"}

        result1 = state.add_extracted_member(member)
        result2 = state.add_extracted_member(member)

        assert result1 is True
        assert result2 is False
        assert len(state.extracted_members) == 1

    def test_add_duplicate_member_by_name_only(self):
        """Test that deduplication works by name even if other fields differ."""
        state = PartyScrapingState(
            current_url="https://example.com",
            party_name="Test Party",
            party_id=1,
            max_depth=3,
        )

        member1: PoliticianMemberData = {"name": "John Doe", "position": "Senator"}
        member2: PoliticianMemberData = {"name": "John Doe", "position": "Governor"}

        result1 = state.add_extracted_member(member1)
        result2 = state.add_extracted_member(member2)

        assert result1 is True
        assert result2 is False
        assert len(state.extracted_members) == 1
        assert state.extracted_members[0].get("position") == "Senator"

    def test_add_member_without_name_raises_error(self):
        """Test that member without name raises ValueError."""
        state = PartyScrapingState(
            current_url="https://example.com",
            party_name="Test Party",
            party_id=1,
            max_depth=3,
        )

        with pytest.raises(ValueError, match="must have a non-empty 'name' field"):
            state.add_extracted_member({"position": "Senator"})  # type: ignore

    def test_add_member_with_empty_name_raises_error(self):
        """Test that member with empty name raises ValueError."""
        state = PartyScrapingState(
            current_url="https://example.com",
            party_name="Test Party",
            party_id=1,
            max_depth=3,
        )

        with pytest.raises(ValueError, match="must have a non-empty 'name' field"):
            state.add_extracted_member({"name": ""})

    def test_add_extracted_members_returns_count(self):
        """Test that add_extracted_members returns count of actually added members."""
        state = PartyScrapingState(
            current_url="https://example.com",
            party_name="Test Party",
            party_id=1,
            max_depth=3,
        )

        members: list[PoliticianMemberData] = [
            {"name": "John Doe"},
            {"name": "Jane Smith"},
            {"name": "John Doe"},  # Duplicate
        ]

        count = state.add_extracted_members(members)

        assert count == 2
        assert len(state.extracted_members) == 2


class TestInputValidation:
    """Tests for input validation."""

    def test_add_pending_url_negative_depth_raises_error(self):
        """Test that negative depth raises ValueError."""
        state = PartyScrapingState(
            current_url="https://example.com",
            party_name="Test Party",
            party_id=1,
            max_depth=3,
        )

        with pytest.raises(ValueError, match="Depth cannot be negative"):
            state.add_pending_url("https://example.com/page", -1)


class TestQueueOperations:
    """Tests for queue operations with deque."""

    def test_uses_deque_internally(self):
        """Test that pending_urls uses deque internally for O(1) operations."""
        state = PartyScrapingState(
            current_url="https://example.com",
            party_name="Test Party",
            party_id=1,
            max_depth=3,
        )

        # Access private field to verify implementation
        assert isinstance(state._pending_urls, deque)  # type: ignore[attr-defined]

    def test_fifo_order_with_deque(self):
        """Test that URLs are popped in FIFO order."""
        state = PartyScrapingState(
            current_url="https://example.com",
            party_name="Test Party",
            party_id=1,
            max_depth=3,
        )

        state.add_pending_url("https://example.com/page1", 1)
        state.add_pending_url("https://example.com/page2", 1)
        state.add_pending_url("https://example.com/page3", 1)

        result1 = state.pop_next_url()
        result2 = state.pop_next_url()
        result3 = state.pop_next_url()

        assert result1 == ("https://example.com/page1", 1)
        assert result2 == ("https://example.com/page2", 1)
        assert result3 == ("https://example.com/page3", 1)


class TestMethodReturnValues:
    """Tests for method return values."""

    def test_add_pending_url_returns_true_when_added(self):
        """Test that add_pending_url returns True when URL is added."""
        state = PartyScrapingState(
            current_url="https://example.com",
            party_name="Test Party",
            party_id=1,
            max_depth=3,
        )

        result = state.add_pending_url("https://example.com/page", 1)

        assert result is True

    def test_add_pending_url_returns_false_when_visited(self):
        """Test that add_pending_url returns False when URL already visited."""
        state = PartyScrapingState(
            current_url="https://example.com",
            party_name="Test Party",
            party_id=1,
            max_depth=3,
        )

        state.mark_visited("https://example.com/page")
        result = state.add_pending_url("https://example.com/page", 1)

        assert result is False

    def test_add_pending_url_returns_false_when_exceeds_depth(self):
        """Test that add_pending_url returns False when depth exceeds max."""
        state = PartyScrapingState(
            current_url="https://example.com",
            party_name="Test Party",
            party_id=1,
            max_depth=2,
        )

        result = state.add_pending_url("https://example.com/page", 3)

        assert result is False

    def test_add_extracted_member_returns_true_when_added(self):
        """Test that add_extracted_member returns True when member is added."""
        state = PartyScrapingState(
            current_url="https://example.com",
            party_name="Test Party",
            party_id=1,
            max_depth=3,
        )

        result = state.add_extracted_member({"name": "John Doe"})

        assert result is True


class TestCompletion:
    """Tests for completion checking."""

    def test_is_complete_empty_queue(self):
        """Test is_complete returns True when no pending URLs."""
        state = PartyScrapingState(
            current_url="https://example.com",
            party_name="Test Party",
            party_id=1,
            max_depth=3,
        )

        assert state.is_complete() is True

    def test_is_complete_with_pending_urls(self):
        """Test is_complete returns False when URLs are pending."""
        state = PartyScrapingState(
            current_url="https://example.com",
            party_name="Test Party",
            party_id=1,
            max_depth=3,
        )

        state.add_pending_url("https://example.com/page", 1)

        assert state.is_complete() is False


class TestDepthChecking:
    """Tests for depth checking."""

    def test_at_max_depth(self):
        """Test checking if at maximum depth."""
        state = PartyScrapingState(
            current_url="https://example.com",
            party_name="Test Party",
            party_id=1,
            max_depth=2,
            depth=2,
        )

        assert state.at_max_depth() is True

    def test_not_at_max_depth(self):
        """Test checking if below maximum depth."""
        state = PartyScrapingState(
            current_url="https://example.com",
            party_name="Test Party",
            party_id=1,
            max_depth=3,
            depth=1,
        )

        assert state.at_max_depth() is False


class TestCounters:
    """Tests for counter methods."""

    def test_total_extracted(self):
        """Test getting total extracted members count."""
        state = PartyScrapingState(
            current_url="https://example.com",
            party_name="Test Party",
            party_id=1,
            max_depth=3,
        )

        state.add_extracted_member({"name": "John Doe"})
        state.add_extracted_member({"name": "Jane Smith"})

        assert state.total_extracted() == 2

    def test_total_pending(self):
        """Test getting total pending URLs count."""
        state = PartyScrapingState(
            current_url="https://example.com",
            party_name="Test Party",
            party_id=1,
            max_depth=3,
        )

        state.add_pending_url("https://example.com/page1", 1)

        assert state.total_pending() == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
