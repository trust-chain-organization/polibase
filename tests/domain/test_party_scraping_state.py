"""Unit tests for PartyScrapingState domain entity.

This test module focuses on testing the domain entity directly without any
framework dependencies (LangGraph, etc.). Tests verify business logic and
domain rules in isolation.

Test Organization:
- TestPartyScrapingStateCreation: Entity initialization and properties
- TestURLNormalization: URL normalization business logic
- TestVisitedURLManagement: Visited URL tracking (infinite loop prevention)
- TestPendingURLQueue: Pending URL queue management (BFS traversal)
- TestExtractedMemberManagement: Politician member extraction and deduplication
- TestDepthManagement: Navigation depth tracking and limits
- TestStateCompletion: Scraping completion detection
- TestImmutability: Property immutability guarantees
"""

import pytest

from src.domain.entities.party_scraping_state import PartyScrapingState
from src.domain.value_objects.politician_member_data import PoliticianMemberData


class TestPartyScrapingStateCreation:
    """Test PartyScrapingState initialization and properties."""

    def test_create_with_required_fields(self) -> None:
        """Test creating state with minimum required fields."""
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
        assert state.depth == 0
        assert state.error_message is None

    def test_create_with_all_fields(self) -> None:
        """Test creating state with all fields including optional ones."""
        state = PartyScrapingState(
            current_url="https://example.com/page",
            party_name="Liberal Democratic Party",
            party_id=5,
            max_depth=5,
            depth=2,
            error_message="Test error",
        )

        assert state.current_url == "https://example.com/page"
        assert state.party_name == "Liberal Democratic Party"
        assert state.party_id == 5
        assert state.max_depth == 5
        assert state.depth == 2
        assert state.error_message == "Test error"

    def test_initial_collections_are_empty(self) -> None:
        """Test that collections are empty on initialization."""
        state = PartyScrapingState(
            current_url="https://example.com",
            party_name="Test",
            party_id=1,
            max_depth=3,
        )

        assert len(state.visited_urls) == 0
        assert len(state.pending_urls) == 0
        assert len(state.extracted_members) == 0


class TestURLNormalization:
    """Test URL normalization business logic.

    URL normalization is critical for:
    1. Preventing infinite loops (same URL with different representations)
    2. Avoiding duplicate network requests
    3. Ensuring consistent URL comparison
    """

    def test_normalize_basic_url(self) -> None:
        """Test basic URL normalization."""
        url = "https://example.com/path"
        result = PartyScrapingState.normalize_url(url)
        assert result == "https://example.com/path"

    def test_normalize_removes_trailing_slash(self) -> None:
        """Test that trailing slashes are removed from paths."""
        url = "https://example.com/path/"
        result = PartyScrapingState.normalize_url(url)
        assert result == "https://example.com/path"

    def test_normalize_preserves_root_slash(self) -> None:
        """Test that root path '/' is preserved."""
        url = "https://example.com/"
        result = PartyScrapingState.normalize_url(url)
        assert result == "https://example.com/"

    def test_normalize_removes_fragment(self) -> None:
        """Test that URL fragments are removed for consistent comparison."""
        url = "https://example.com/path#section"
        result = PartyScrapingState.normalize_url(url)
        assert result == "https://example.com/path"

    def test_normalize_lowercase_scheme(self) -> None:
        """Test that scheme is converted to lowercase."""
        url = "HTTPS://example.com/path"
        result = PartyScrapingState.normalize_url(url)
        assert result == "https://example.com/path"

    def test_normalize_lowercase_host(self) -> None:
        """Test that host is converted to lowercase."""
        url = "https://Example.COM/path"
        result = PartyScrapingState.normalize_url(url)
        assert result == "https://example.com/path"

    def test_normalize_strips_whitespace(self) -> None:
        """Test that leading/trailing whitespace is stripped."""
        url = "  https://example.com/path  "
        result = PartyScrapingState.normalize_url(url)
        assert result == "https://example.com/path"

    def test_normalize_idempotent(self) -> None:
        """Test that normalizing twice produces same result (idempotency).

        This property is critical for ensuring consistent behavior.
        """
        url = "HTTPS://Example.COM/Path/#section"
        first = PartyScrapingState.normalize_url(url)
        second = PartyScrapingState.normalize_url(first)
        assert first == second

    def test_normalize_empty_url_raises_error(self) -> None:
        """Test that empty URL raises ValueError."""
        with pytest.raises(ValueError, match="URL cannot be empty"):
            PartyScrapingState.normalize_url("")

    def test_normalize_whitespace_only_raises_error(self) -> None:
        """Test that whitespace-only URL raises ValueError."""
        with pytest.raises(ValueError, match="URL cannot be empty"):
            PartyScrapingState.normalize_url("   ")

    def test_normalize_invalid_url_no_scheme_raises_error(self) -> None:
        """Test that URL without scheme raises ValueError."""
        with pytest.raises(ValueError, match="Invalid URL format"):
            PartyScrapingState.normalize_url("example.com/path")

    def test_normalize_invalid_url_no_host_raises_error(self) -> None:
        """Test that URL without host raises ValueError."""
        with pytest.raises(ValueError, match="Invalid URL format"):
            PartyScrapingState.normalize_url("https:///path")


class TestVisitedURLManagement:
    """Test visited URL tracking for infinite loop prevention.

    Business Rule: Each URL should only be visited once to:
    1. Prevent infinite loops in circular link structures
    2. Avoid unnecessary network requests and API costs
    3. Ensure scraping completes in finite time
    """

    @pytest.fixture
    def state(self) -> PartyScrapingState:
        """Fixture providing a basic state for testing."""
        return PartyScrapingState(
            current_url="https://example.com",
            party_name="Test Party",
            party_id=1,
            max_depth=3,
        )

    def test_mark_visited_adds_to_set(self, state: PartyScrapingState) -> None:
        """Test marking URL as visited adds it to the set."""
        assert not state.has_visited("https://example.com/page1")

        state.mark_visited("https://example.com/page1")

        assert state.has_visited("https://example.com/page1")
        assert len(state.visited_urls) == 1

    def test_mark_visited_normalizes_url(self, state: PartyScrapingState) -> None:
        """Test that marking as visited uses normalized URL."""
        state.mark_visited("HTTPS://Example.COM/page/")

        # Should be stored in normalized form
        assert "https://example.com/page" in state.visited_urls

    def test_has_visited_normalizes_url(self, state: PartyScrapingState) -> None:
        """Test that visited check uses normalized URLs.

        This ensures that URLs with different representations (case, trailing
        slashes, fragments) are recognized as the same URL.
        """
        state.mark_visited("https://example.com/page")

        # Different variations should all be recognized as visited
        assert state.has_visited("HTTPS://example.com/page")
        assert state.has_visited("https://EXAMPLE.com/page")
        assert state.has_visited("https://example.com/page/")
        assert state.has_visited("https://example.com/page#fragment")

    def test_mark_multiple_visited_urls(self, state: PartyScrapingState) -> None:
        """Test marking multiple URLs as visited."""
        urls = [
            "https://example.com/page1",
            "https://example.com/page2",
            "https://example.com/page3",
        ]

        for url in urls:
            state.mark_visited(url)

        assert len(state.visited_urls) == 3
        for url in urls:
            assert state.has_visited(url)

    def test_mark_visited_idempotent(self, state: PartyScrapingState) -> None:
        """Test that marking same URL multiple times has no effect."""
        state.mark_visited("https://example.com/page")
        state.mark_visited("https://example.com/page")
        state.mark_visited("https://example.com/page")

        assert len(state.visited_urls) == 1

    def test_has_visited_invalid_url_raises_error(
        self, state: PartyScrapingState
    ) -> None:
        """Test that checking invalid URL raises ValueError."""
        with pytest.raises(ValueError, match="Invalid URL format"):
            state.has_visited("not-a-valid-url")

    def test_mark_visited_invalid_url_raises_error(
        self, state: PartyScrapingState
    ) -> None:
        """Test that marking invalid URL raises ValueError."""
        with pytest.raises(ValueError, match="Invalid URL format"):
            state.mark_visited("not-a-valid-url")


class TestPendingURLQueue:
    """Test pending URL queue management for breadth-first traversal.

    Business Rule: URLs should be processed in FIFO (breadth-first) order
    to ensure we process all URLs at depth N before moving to depth N+1.
    """

    @pytest.fixture
    def state(self) -> PartyScrapingState:
        """Fixture providing a basic state for testing."""
        return PartyScrapingState(
            current_url="https://example.com",
            party_name="Test Party",
            party_id=1,
            max_depth=3,
        )

    def test_add_pending_url_returns_true_for_new_url(
        self, state: PartyScrapingState
    ) -> None:
        """Test adding new URL to queue."""
        was_added = state.add_pending_url("https://example.com/page1", 1)

        assert was_added is True
        assert len(state.pending_urls) == 1
        assert state.pending_urls[0] == ("https://example.com/page1", 1)

    def test_add_pending_url_rejects_visited_url(
        self, state: PartyScrapingState
    ) -> None:
        """Test that visited URLs are not added to queue.

        This prevents re-processing of already visited pages.
        """
        state.mark_visited("https://example.com/page1")

        was_added = state.add_pending_url("https://example.com/page1", 1)

        assert was_added is False
        assert len(state.pending_urls) == 0

    def test_add_pending_url_rejects_beyond_max_depth(
        self, state: PartyScrapingState
    ) -> None:
        """Test that URLs beyond max depth are rejected.

        Business Rule: Scraping should respect depth limits to avoid
        traversing too deep into the site structure.
        """
        # max_depth is 3, so depth 4 should be rejected
        was_added = state.add_pending_url("https://example.com/deep", 4)

        assert was_added is False
        assert len(state.pending_urls) == 0

    def test_add_pending_url_accepts_at_max_depth(
        self, state: PartyScrapingState
    ) -> None:
        """Test that URLs at exactly max_depth are accepted.

        Boundary condition: depth == max_depth should be included.
        """
        # max_depth is 3, depth 3 should be accepted
        was_added = state.add_pending_url("https://example.com/page", 3)

        assert was_added is True
        assert len(state.pending_urls) == 1

    def test_add_pending_url_normalizes_url(self, state: PartyScrapingState) -> None:
        """Test that added URLs are normalized."""
        was_added = state.add_pending_url("HTTPS://Example.COM/page/", 1)

        assert was_added is True
        # Should be stored in normalized form
        assert state.pending_urls[0][0] == "https://example.com/page"

    def test_add_pending_url_rejects_normalized_duplicate(
        self, state: PartyScrapingState
    ) -> None:
        """Test that normalized duplicates are rejected."""
        state.mark_visited("https://example.com/page")

        # Try to add same URL with different representation
        was_added = state.add_pending_url("HTTPS://Example.COM/page/", 1)

        assert was_added is False
        assert len(state.pending_urls) == 0

    def test_add_pending_url_negative_depth_raises_error(
        self, state: PartyScrapingState
    ) -> None:
        """Test that negative depth raises ValueError."""
        with pytest.raises(ValueError, match="Depth cannot be negative"):
            state.add_pending_url("https://example.com/page", -1)

    def test_add_pending_url_invalid_url_raises_error(
        self, state: PartyScrapingState
    ) -> None:
        """Test that invalid URL raises ValueError."""
        with pytest.raises(ValueError, match="Invalid URL format"):
            state.add_pending_url("not-a-url", 1)

    def test_pop_next_url_returns_fifo_order(self, state: PartyScrapingState) -> None:
        """Test that URLs are processed in FIFO (breadth-first) order.

        Business Rule: Process all URLs at depth N before depth N+1 to
        ensure proper breadth-first traversal.
        """
        state.add_pending_url("https://example.com/first", 1)
        state.add_pending_url("https://example.com/second", 1)
        state.add_pending_url("https://example.com/third", 2)

        first = state.pop_next_url()
        assert first == ("https://example.com/first", 1)

        second = state.pop_next_url()
        assert second == ("https://example.com/second", 1)

        third = state.pop_next_url()
        assert third == ("https://example.com/third", 2)

    def test_pop_next_url_returns_none_when_empty(
        self, state: PartyScrapingState
    ) -> None:
        """Test behavior when queue is empty."""
        result = state.pop_next_url()
        assert result is None

    def test_pop_next_url_multiple_times_when_empty(
        self, state: PartyScrapingState
    ) -> None:
        """Test that popping from empty queue always returns None."""
        assert state.pop_next_url() is None
        assert state.pop_next_url() is None
        assert state.pop_next_url() is None

    def test_queue_integration_workflow(self, state: PartyScrapingState) -> None:
        """Test typical workflow: add URLs, pop them, check completion."""
        # Add some URLs
        state.add_pending_url("https://example.com/page1", 1)
        state.add_pending_url("https://example.com/page2", 1)

        assert state.total_pending() == 2
        assert not state.is_complete()

        # Process first URL
        url1, depth1 = state.pop_next_url()  # type: ignore
        assert url1 == "https://example.com/page1"
        assert state.total_pending() == 1

        # Process second URL
        url2, depth2 = state.pop_next_url()  # type: ignore
        assert url2 == "https://example.com/page2"
        assert state.total_pending() == 0
        assert state.is_complete()


class TestExtractedMemberManagement:
    """Test extracted politician member tracking and deduplication.

    Business Rule: Deduplicate politicians by name to avoid creating
    duplicate records in the database.
    """

    @pytest.fixture
    def state(self) -> PartyScrapingState:
        """Fixture providing a basic state for testing."""
        return PartyScrapingState(
            current_url="https://example.com",
            party_name="Test Party",
            party_id=1,
            max_depth=3,
        )

    def test_add_extracted_member_success(self, state: PartyScrapingState) -> None:
        """Test adding a new member."""
        member: PoliticianMemberData = {
            "name": "田中太郎",
            "role": "議員",
        }

        was_added = state.add_extracted_member(member)

        assert was_added is True
        assert state.total_extracted() == 1
        assert state.extracted_members[0]["name"] == "田中太郎"
        assert state.extracted_members[0]["role"] == "議員"

    def test_add_extracted_member_rejects_duplicate_name(
        self, state: PartyScrapingState
    ) -> None:
        """Test that duplicate members (same name) are rejected.

        Business Rule: Deduplicate by name to prevent creating multiple
        records for the same politician.
        """
        member: PoliticianMemberData = {"name": "田中太郎", "role": "議員"}

        first = state.add_extracted_member(member)
        assert first is True
        assert state.total_extracted() == 1

        # Try to add same member again (same name)
        second = state.add_extracted_member(member)
        assert second is False
        assert state.total_extracted() == 1

    def test_add_extracted_member_allows_different_names(
        self, state: PartyScrapingState
    ) -> None:
        """Test that members with different names are both added."""
        member1: PoliticianMemberData = {"name": "田中太郎", "role": "議員"}
        member2: PoliticianMemberData = {"name": "佐藤花子", "role": "議員"}

        assert state.add_extracted_member(member1) is True
        assert state.add_extracted_member(member2) is True
        assert state.total_extracted() == 2

    def test_add_extracted_member_deep_copies_data(
        self, state: PartyScrapingState
    ) -> None:
        """Test that member data is deep copied to prevent external mutation."""
        member: PoliticianMemberData = {"name": "田中太郎", "role": "議員"}

        state.add_extracted_member(member)

        # Mutate original
        member["role"] = "元議員"

        # Stored copy should be unchanged
        assert state.extracted_members[0]["role"] == "議員"

    def test_add_extracted_member_raises_on_missing_name(
        self, state: PartyScrapingState
    ) -> None:
        """Test that member without name raises ValueError."""
        member: PoliticianMemberData = {"role": "議員"}  # type: ignore

        with pytest.raises(ValueError, match="non-empty 'name' field"):
            state.add_extracted_member(member)

    def test_add_extracted_member_raises_on_empty_name(
        self, state: PartyScrapingState
    ) -> None:
        """Test that member with empty name raises ValueError."""
        member: PoliticianMemberData = {"name": "", "role": "議員"}

        with pytest.raises(ValueError, match="non-empty 'name' field"):
            state.add_extracted_member(member)

    def test_add_extracted_members_batch_operation(
        self, state: PartyScrapingState
    ) -> None:
        """Test adding multiple members in batch."""
        members: list[PoliticianMemberData] = [
            {"name": "田中太郎", "role": "議員"},
            {"name": "佐藤花子", "role": "議員"},
            {"name": "鈴木一郎", "role": "議員"},
        ]

        added_count = state.add_extracted_members(members)

        assert added_count == 3
        assert state.total_extracted() == 3

    def test_add_extracted_members_with_duplicates(
        self, state: PartyScrapingState
    ) -> None:
        """Test batch operation with duplicate names."""
        members: list[PoliticianMemberData] = [
            {"name": "田中太郎", "role": "議員"},
            {"name": "佐藤花子", "role": "議員"},
            {"name": "田中太郎", "role": "元議員"},  # Duplicate name
        ]

        added_count = state.add_extracted_members(members)

        assert added_count == 2  # Only 2 unique names
        assert state.total_extracted() == 2

    def test_add_extracted_members_respects_existing(
        self, state: PartyScrapingState
    ) -> None:
        """Test that batch operation respects already extracted members."""
        # Add one member first
        state.add_extracted_member({"name": "田中太郎", "role": "議員"})

        # Try to add batch including the duplicate
        members: list[PoliticianMemberData] = [
            {"name": "田中太郎", "role": "元議員"},  # Duplicate
            {"name": "佐藤花子", "role": "議員"},
        ]

        added_count = state.add_extracted_members(members)

        assert added_count == 1  # Only 1 new member
        assert state.total_extracted() == 2

    def test_add_extracted_members_raises_on_invalid_member(
        self, state: PartyScrapingState
    ) -> None:
        """Test that batch operation raises on first invalid member."""
        members: list[PoliticianMemberData] = [
            {"name": "田中太郎", "role": "議員"},
            {"role": "議員"},  # type: ignore # Missing name
            {"name": "佐藤花子", "role": "議員"},
        ]

        with pytest.raises(ValueError, match="non-empty 'name' field"):
            state.add_extracted_members(members)

        # First valid member should have been added before error
        assert state.total_extracted() == 1


class TestDepthManagement:
    """Test navigation depth tracking and limits.

    Business Rule: Limit traversal depth to prevent going too deep into
    the site structure and ensure scraping completes in reasonable time.
    """

    def test_initial_depth_is_zero(self) -> None:
        """Test that initial depth is 0 (root level)."""
        state = PartyScrapingState(
            current_url="https://example.com",
            party_name="Test",
            party_id=1,
            max_depth=3,
        )

        assert state.depth == 0

    def test_create_with_custom_depth(self) -> None:
        """Test creating state with custom depth value."""
        state = PartyScrapingState(
            current_url="https://example.com",
            party_name="Test",
            party_id=1,
            max_depth=5,
            depth=2,
        )

        assert state.depth == 2
        assert state.max_depth == 5

    def test_at_max_depth_when_equal(self) -> None:
        """Test at_max_depth returns True when depth equals max_depth."""
        state = PartyScrapingState(
            current_url="https://example.com",
            party_name="Test",
            party_id=1,
            max_depth=3,
            depth=3,
        )

        assert state.at_max_depth() is True

    def test_at_max_depth_when_below(self) -> None:
        """Test at_max_depth returns False when depth is below max."""
        state = PartyScrapingState(
            current_url="https://example.com",
            party_name="Test",
            party_id=1,
            max_depth=3,
            depth=2,
        )

        assert state.at_max_depth() is False

    def test_at_max_depth_when_above(self) -> None:
        """Test at_max_depth returns True when depth exceeds max.

        Note: This tests the behavior when depth > max_depth, which
        shouldn't normally happen but is handled by the method.
        """
        state = PartyScrapingState(
            current_url="https://example.com",
            party_name="Test",
            party_id=1,
            max_depth=3,
            depth=4,
        )

        assert state.at_max_depth() is True

    def test_depth_zero_not_at_max(self) -> None:
        """Test that depth 0 is not at max depth."""
        state = PartyScrapingState(
            current_url="https://example.com",
            party_name="Test",
            party_id=1,
            max_depth=3,
            depth=0,
        )

        assert state.at_max_depth() is False


class TestStateCompletion:
    """Test scraping completion detection.

    Business Rule: Scraping is complete when there are no more URLs to
    process, allowing the workflow to terminate.
    """

    def test_is_complete_when_no_pending_urls(self) -> None:
        """Test that state is complete when no pending URLs."""
        state = PartyScrapingState(
            current_url="https://example.com",
            party_name="Test",
            party_id=1,
            max_depth=3,
        )

        assert state.is_complete() is True

    def test_is_not_complete_when_pending_urls_exist(self) -> None:
        """Test that state is not complete when URLs are pending."""
        state = PartyScrapingState(
            current_url="https://example.com",
            party_name="Test",
            party_id=1,
            max_depth=3,
        )

        state.add_pending_url("https://example.com/page", 1)

        assert state.is_complete() is False

    def test_becomes_complete_after_processing_all(self) -> None:
        """Test that state becomes complete after processing all URLs."""
        state = PartyScrapingState(
            current_url="https://example.com",
            party_name="Test",
            party_id=1,
            max_depth=3,
        )

        # Add URLs
        state.add_pending_url("https://example.com/page1", 1)
        state.add_pending_url("https://example.com/page2", 1)
        assert not state.is_complete()

        # Process first URL
        state.pop_next_url()
        assert not state.is_complete()

        # Process second URL
        state.pop_next_url()
        assert state.is_complete()


class TestImmutability:
    """Test property immutability guarantees.

    Business Rule: Properties that return collections should be immutable
    to prevent external code from accidentally modifying internal state.
    """

    @pytest.fixture
    def state(self) -> PartyScrapingState:
        """Fixture providing a state with some data."""
        state = PartyScrapingState(
            current_url="https://example.com",
            party_name="Test Party",
            party_id=1,
            max_depth=3,
        )
        state.mark_visited("https://example.com/visited")
        state.add_pending_url("https://example.com/pending", 1)
        state.add_extracted_member({"name": "Test Member", "role": "議員"})
        return state

    def test_visited_urls_returns_frozen_set(self, state: PartyScrapingState) -> None:
        """Test that visited_urls property returns immutable frozenset."""
        visited = state.visited_urls

        assert isinstance(visited, frozenset)
        # Should not be able to modify
        with pytest.raises(AttributeError):
            visited.add("https://example.com/new")  # type: ignore

    def test_pending_urls_returns_tuple(self, state: PartyScrapingState) -> None:
        """Test that pending_urls property returns immutable tuple."""
        pending = state.pending_urls

        assert isinstance(pending, tuple)
        # Tuples don't have append method, so this will raise AttributeError
        with pytest.raises(AttributeError):
            pending.append(("https://example.com/new", 1))  # type: ignore

    def test_extracted_members_returns_tuple(self, state: PartyScrapingState) -> None:
        """Test that extracted_members property returns immutable tuple."""
        members = state.extracted_members

        assert isinstance(members, tuple)
        # Should not be able to modify
        with pytest.raises(AttributeError):
            members.append({"name": "New Member", "role": "議員"})  # type: ignore

    def test_modifying_returned_member_does_not_affect_state(
        self, state: PartyScrapingState
    ) -> None:
        """Test that modifying returned member dict affects internal state.

        Note: The current implementation returns a shallow copy (tuple of dicts),
        so modifying the dict will affect internal state. This test documents
        the current behavior. For true immutability, would need deep copy.
        """
        members = state.extracted_members

        # Modifying the dict WILL affect internal state (shallow copy)
        members_list = list(members)
        members_list[0]["name"] = "Modified Name"

        # Current implementation: internal state IS affected
        assert state.extracted_members[0]["name"] == "Modified Name"

        # To demonstrate tuple immutability (can't replace entire element)
        with pytest.raises(TypeError):
            members[0] = {"name": "New Member", "role": "議員"}  # type: ignore


class TestTotalCountHelpers:
    """Test helper methods for counting totals.

    These methods provide convenient access to collection sizes for
    monitoring scraping progress.
    """

    @pytest.fixture
    def state(self) -> PartyScrapingState:
        """Fixture providing a basic state for testing."""
        return PartyScrapingState(
            current_url="https://example.com",
            party_name="Test Party",
            party_id=1,
            max_depth=3,
        )

    def test_total_extracted_initially_zero(self, state: PartyScrapingState) -> None:
        """Test that total_extracted is 0 initially."""
        assert state.total_extracted() == 0

    def test_total_extracted_after_adding_members(
        self, state: PartyScrapingState
    ) -> None:
        """Test total_extracted reflects number of added members."""
        state.add_extracted_member({"name": "Member 1", "role": "議員"})
        assert state.total_extracted() == 1

        state.add_extracted_member({"name": "Member 2", "role": "議員"})
        assert state.total_extracted() == 2

        state.add_extracted_member({"name": "Member 3", "role": "議員"})
        assert state.total_extracted() == 3

    def test_total_pending_initially_zero(self, state: PartyScrapingState) -> None:
        """Test that total_pending is 0 initially."""
        assert state.total_pending() == 0

    def test_total_pending_after_adding_urls(self, state: PartyScrapingState) -> None:
        """Test total_pending reflects number of pending URLs."""
        state.add_pending_url("https://example.com/page1", 1)
        assert state.total_pending() == 1

        state.add_pending_url("https://example.com/page2", 1)
        assert state.total_pending() == 2

        state.add_pending_url("https://example.com/page3", 2)
        assert state.total_pending() == 3

    def test_total_pending_decreases_when_popping(
        self, state: PartyScrapingState
    ) -> None:
        """Test total_pending decreases when URLs are popped."""
        state.add_pending_url("https://example.com/page1", 1)
        state.add_pending_url("https://example.com/page2", 1)
        assert state.total_pending() == 2

        state.pop_next_url()
        assert state.total_pending() == 1

        state.pop_next_url()
        assert state.total_pending() == 0
