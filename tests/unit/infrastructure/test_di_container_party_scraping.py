"""Test DI container configuration for party scraping.

This module verifies that the dependency injection container correctly wires
all dependencies required for hierarchical party scraping.
"""

from src.infrastructure.di.container import init_container


class TestDIContainerPartyScrapingWiring:
    """Test that DI container correctly wires party scraping dependencies."""

    def test_party_scraping_agent_is_registered(self):
        """Test that IPartyScrapingAgent is registered in container."""
        container = init_container()

        # Should not raise
        agent = container.use_cases.party_scraping_agent()

        assert agent is not None
        from src.domain.services.interfaces.party_scraping_agent import (
            IPartyScrapingAgent,
        )

        assert isinstance(agent, IPartyScrapingAgent)

    def test_agent_receives_page_classifier(self):
        """Test that Agent receives IPageClassifierService."""
        container = init_container()

        agent = container.use_cases.party_scraping_agent()

        # Agent should have page_classifier injected
        assert hasattr(agent, "_page_classifier")
        assert agent._page_classifier is not None

        from src.domain.services.interfaces.page_classifier_service import (
            IPageClassifierService,
        )

        assert isinstance(agent._page_classifier, IPageClassifierService)

    def test_agent_receives_member_extractor(self):
        """Test that Agent receives IPartyMemberExtractionService."""
        container = init_container()

        agent = container.use_cases.party_scraping_agent()

        # Agent should have member_extractor injected
        assert hasattr(agent, "_member_extractor")
        assert agent._member_extractor is not None

        from src.domain.services.party_member_extraction_service import (
            IPartyMemberExtractionService,
        )

        assert isinstance(agent._member_extractor, IPartyMemberExtractionService)

    def test_agent_receives_link_analyzer(self):
        """Test that Agent receives ILinkAnalyzerService."""
        container = init_container()

        agent = container.use_cases.party_scraping_agent()

        # Agent should have link_analyzer injected
        assert hasattr(agent, "_link_analyzer")
        assert agent._link_analyzer is not None

        from src.domain.services.interfaces.link_analyzer_service import (
            ILinkAnalyzerService,
        )

        assert isinstance(agent._link_analyzer, ILinkAnalyzerService)

    def test_agent_receives_scraper(self):
        """Test that Agent receives IWebScraperService."""
        container = init_container()

        agent = container.use_cases.party_scraping_agent()

        # Agent should have scraper injected
        assert hasattr(agent, "_scraper")
        assert agent._scraper is not None

        # Verify scraper has required methods
        assert hasattr(agent._scraper, "fetch_html")
        assert callable(agent._scraper.fetch_html)

    def test_container_can_be_reinitialized(self):
        """Test that container can be initialized multiple times."""
        container1 = init_container()
        agent1 = container1.use_cases.party_scraping_agent()

        container2 = init_container()
        agent2 = container2.use_cases.party_scraping_agent()

        # Should create new instances
        assert agent1 is not agent2

    def test_agent_is_properly_initialized(self):
        """Test that Agent is initialized and ready to use."""
        container = init_container()

        agent = container.use_cases.party_scraping_agent()

        # Agent should have is_initialized method
        assert hasattr(agent, "is_initialized")
        assert callable(agent.is_initialized)

        # Agent should be initialized
        assert agent.is_initialized() is True
