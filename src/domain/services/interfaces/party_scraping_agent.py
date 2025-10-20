"""Party scraping agent interface for domain layer."""

from abc import ABC, abstractmethod

from src.domain.entities.party_scraping_state import PartyScrapingState


class IPartyScrapingAgent(ABC):
    """Interface for hierarchical party member scraping agents.

    This interface defines the contract for agents that can navigate
    hierarchical party member pages and extract politician information.
    It belongs to the domain layer as it represents a core business capability.

    The actual implementation (e.g., using LangGraph, state machines, etc.)
    is an infrastructure concern and should not leak into the domain.
    """

    @abstractmethod
    async def scrape(self, initial_state: PartyScrapingState) -> PartyScrapingState:
        """Execute hierarchical scraping starting from the initial state.

        This method navigates through party member pages, following links
        to child pages up to the maximum depth, and extracts politician
        information from member list pages.

        Args:
            initial_state: Initial scraping state containing:
                - current_url: Starting URL
                - party_name: Name of the party
                - party_id: Database ID of the party
                - max_depth: Maximum navigation depth
                - Other state fields initialized as needed

        Returns:
            Final state containing:
                - extracted_members: List of all extracted politicians
                - visited_urls: All URLs that were visited
                - error_message: Error message if scraping failed

        Raises:
            ValueError: If initial_state is invalid
            RuntimeError: If scraping fails catastrophically
        """
        ...

    @abstractmethod
    def is_initialized(self) -> bool:
        """Check if the agent is properly initialized and ready to scrape.

        Returns:
            True if agent is ready, False otherwise
        """
        ...
