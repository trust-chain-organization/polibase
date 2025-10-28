"""Unit tests for LangGraph party scraping agent implementation."""

from unittest.mock import patch

import pytest

from src.domain.entities.party_scraping_state import PartyScrapingState
from src.domain.value_objects.politician_member_data import PoliticianMemberData
from src.infrastructure.external.langgraph_party_scraping_agent import (
    LangGraphPartyScrapingAgent,
)
from src.infrastructure.external.langgraph_state_adapter import (
    domain_to_langgraph_state,
    langgraph_to_domain_state,
)


class TestStateAdapterDeepCopy:
    """Tests for deep copy behavior in state adapter."""

    def test_domain_to_langgraph_deep_copies_members(self):
        """Test that domain → LangGraph conversion deep copies members."""
        original_member: PoliticianMemberData = {
            "name": "John Doe",
            "position": "Senator",
        }
        domain_state = PartyScrapingState(
            current_url="https://example.com",
            party_name="Test Party",
            party_id=1,
            max_depth=3,
        )
        domain_state.add_extracted_member(original_member)

        lg_state = domain_to_langgraph_state(domain_state)

        # Mutate original member
        original_member["position"] = "Governor"

        # LangGraph state should not be affected
        assert lg_state["extracted_members"][0]["position"] == "Senator"

    def test_langgraph_to_domain_deep_copies_members(self):
        """Test that LangGraph → domain conversion deep copies members."""
        original_member: PoliticianMemberData = {
            "name": "Jane Smith",
            "position": "Mayor",
        }
        domain_state = PartyScrapingState(
            current_url="https://example.com",
            party_name="Test Party",
            party_id=1,
            max_depth=3,
        )
        domain_state.add_extracted_member(original_member)

        lg_state = domain_to_langgraph_state(domain_state)
        result_state = langgraph_to_domain_state(lg_state)

        # Mutate LangGraph state
        lg_state["extracted_members"][0]["position"] = "Governor"

        # Domain state should not be affected
        assert result_state.extracted_members[0].get("position") == "Mayor"


class TestLangGraphStateAdapter:
    """Tests for state conversion between domain and LangGraph."""

    def test_domain_to_langgraph_conversion(self):
        """Test converting domain state to LangGraph state."""
        domain_state = PartyScrapingState(
            current_url="https://example.com",
            party_name="Test Party",
            party_id=1,
            max_depth=3,
        )

        lg_state = domain_to_langgraph_state(domain_state)

        assert lg_state["current_url"] == "https://example.com"
        assert lg_state["party_name"] == "Test Party"
        assert lg_state["party_id"] == 1
        assert lg_state["max_depth"] == 3
        assert len(lg_state["messages"]) > 0

    def test_langgraph_to_domain_conversion(self):
        """Test converting LangGraph state back to domain state."""
        domain_state = PartyScrapingState(
            current_url="https://example.com",
            party_name="Test Party",
            party_id=1,
            max_depth=3,
        )
        domain_state.add_extracted_member({"name": "John Doe"})

        lg_state = domain_to_langgraph_state(domain_state)
        result_state = langgraph_to_domain_state(lg_state)

        assert result_state.current_url == domain_state.current_url
        assert result_state.party_name == domain_state.party_name
        assert result_state.party_id == domain_state.party_id
        assert len(result_state.extracted_members) == 1

    def test_roundtrip_conversion(self):
        """Test that domain → LangGraph → domain preserves data."""
        original_state = PartyScrapingState(
            current_url="https://example.com/members",
            party_name="Progressive Party",
            party_id=5,
            max_depth=2,
            depth=1,
        )
        original_state.mark_visited("https://example.com")
        original_state.add_pending_url("https://example.com/page2", 2)
        original_state.add_extracted_member({"name": "Jane Smith"})

        lg_state = domain_to_langgraph_state(original_state)
        result_state = langgraph_to_domain_state(lg_state)

        assert result_state.current_url == original_state.current_url
        assert result_state.party_name == original_state.party_name
        assert result_state.depth == original_state.depth
        assert len(result_state.visited_urls) == len(original_state.visited_urls)
        assert len(result_state.pending_urls) == len(original_state.pending_urls)

    def test_conversion_handles_empty_collections(self):
        """Test that conversion handles empty collections correctly."""
        domain_state = PartyScrapingState(
            current_url="https://example.com",
            party_name="Test Party",
            party_id=1,
            max_depth=3,
        )

        lg_state = domain_to_langgraph_state(domain_state)
        result_state = langgraph_to_domain_state(lg_state)

        assert len(result_state.visited_urls) == 0
        assert len(result_state.pending_urls) == 0
        assert len(result_state.extracted_members) == 0

    def test_conversion_preserves_error_message(self):
        """Test that error_message is preserved through conversions."""
        domain_state = PartyScrapingState(
            current_url="https://example.com",
            party_name="Test Party",
            party_id=1,
            max_depth=3,
            error_message="Test error",
        )

        lg_state = domain_to_langgraph_state(domain_state)
        result_state = langgraph_to_domain_state(lg_state)

        assert result_state.error_message == "Test error"


class TestLangGraphPartyScrapingAgent:
    """Tests for LangGraph party scraping agent."""

    def test_agent_initialization(self):
        """Test that agent initializes successfully."""
        agent = LangGraphPartyScrapingAgent()

        assert agent.is_initialized() is True

    def test_agent_initialization_failure(self):
        """Test that initialization failure is handled correctly."""
        with patch(
            "src.infrastructure.external.langgraph_party_scraping_agent.StateGraph"
        ) as mock_state_graph:
            mock_state_graph.side_effect = RuntimeError("Graph creation failed")

            with pytest.raises(RuntimeError):
                LangGraphPartyScrapingAgent()

    @pytest.mark.asyncio
    async def test_scrape_basic_invocation(self):
        """Test basic scraping invocation."""
        agent = LangGraphPartyScrapingAgent()

        initial_state = PartyScrapingState(
            current_url="https://example.com",
            party_name="Test Party",
            party_id=1,
            max_depth=3,
        )

        result = await agent.scrape(initial_state)

        assert result is not None
        assert result.party_name == "Test Party"
        assert result.party_id == 1

    @pytest.mark.asyncio
    async def test_scrape_with_no_url_raises_error(self):
        """Test that scraping without URL raises ValueError."""
        agent = LangGraphPartyScrapingAgent()

        invalid_state = PartyScrapingState(
            current_url="",
            party_name="Test Party",
            party_id=1,
            max_depth=3,
        )

        with pytest.raises(ValueError, match="current_url"):
            await agent.scrape(invalid_state)

    @pytest.mark.asyncio
    async def test_scrape_preserves_party_info(self):
        """Test that scraping preserves party information."""
        agent = LangGraphPartyScrapingAgent()

        initial_state = PartyScrapingState(
            current_url="https://example.com/members",
            party_name="Progressive Party",
            party_id=5,
            max_depth=2,
        )

        result = await agent.scrape(initial_state)

        assert result.party_name == "Progressive Party"
        assert result.party_id == 5
        assert result.current_url == "https://example.com/members"

    @pytest.mark.asyncio
    async def test_scrape_with_existing_data(self):
        """Test scraping with pre-populated state."""
        agent = LangGraphPartyScrapingAgent()

        initial_state = PartyScrapingState(
            current_url="https://example.com",
            party_name="Test Party",
            party_id=1,
            max_depth=3,
        )
        initial_state.add_extracted_member({"name": "Existing Member"})
        initial_state.mark_visited("https://example.com/visited")

        result = await agent.scrape(initial_state)

        assert result is not None
        # State should be preserved through the scraping process
        assert len(result.visited_urls) >= 1

    @pytest.mark.asyncio
    async def test_scrape_error_does_not_mutate_input(self):
        """Test that scraping error does not mutate input state."""
        agent = LangGraphPartyScrapingAgent()

        initial_state = PartyScrapingState(
            current_url="https://example.com",
            party_name="Test Party",
            party_id=1,
            max_depth=3,
        )

        # Mock the compiled agent to raise an error
        with patch.object(agent, "_compiled_agent") as mock_agent:
            mock_agent.invoke.side_effect = RuntimeError("Scraping failed")

            # Store original error_message
            original_error = initial_state.error_message

            result = await agent.scrape(initial_state)

            # Input state should not be mutated
            assert initial_state.error_message == original_error
            # Result state should have the error
            assert result.error_message is not None
            assert "Scraping failed" in result.error_message

    @pytest.mark.asyncio
    async def test_scrape_uninitialized_agent_raises_error(self):
        """Test that scraping with uninitialized agent raises RuntimeError."""
        agent = LangGraphPartyScrapingAgent()
        agent._is_initialized = False  # Force uninitialized state

        initial_state = PartyScrapingState(
            current_url="https://example.com",
            party_name="Test Party",
            party_id=1,
            max_depth=3,
        )

        with pytest.raises(RuntimeError, match="not initialized"):
            await agent.scrape(initial_state)

    @pytest.mark.asyncio
    async def test_scrape_with_mock_langgraph(self):
        """Test scraping with mocked LangGraph invocation."""
        agent = LangGraphPartyScrapingAgent()

        initial_state = PartyScrapingState(
            current_url="https://example.com",
            party_name="Test Party",
            party_id=1,
            max_depth=3,
        )

        # Mock the compiled agent to return controlled state
        mock_result = {
            "current_url": "https://example.com",
            "party_name": "Test Party",
            "party_id": 1,
            "max_depth": 3,
            "depth": 0,
            "visited_urls": {"https://example.com"},
            "pending_urls": [],
            "extracted_members": [{"name": "Mocked Member"}],
            "messages": [],
            "error_message": None,
            "scraping_config": {
                "max_depth": 2,
                "recursion_limit": 100,
                "min_confidence_threshold": 0.7,
                "max_pages": 1000,
            },
        }

        with patch.object(agent, "_compiled_agent") as mock_agent:
            mock_agent.invoke.return_value = mock_result

            result = await agent.scrape(initial_state)

            assert len(result.extracted_members) == 1
            assert result.extracted_members[0].get("name") == "Mocked Member"
            mock_agent.invoke.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
