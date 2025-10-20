"""Interface for page classification service."""

from abc import ABC, abstractmethod

from src.domain.value_objects.page_classification import PageClassification


class IPageClassifierService(ABC):
    """Interface for classifying web pages during hierarchical navigation.

    This service analyzes web page content to determine its type
    (index page, member list page, or other) to guide the navigation
    strategy in hierarchical party member scraping.
    """

    @abstractmethod
    async def classify_page(
        self,
        html_content: str,
        current_url: str,
        party_name: str = "",
    ) -> PageClassification:
        """Classify a web page to determine navigation strategy.

        Args:
            html_content: HTML content of the page to classify
            current_url: URL of the current page (for context)
            party_name: Name of the political party (optional, for context)

        Returns:
            PageClassification with type, confidence, and metadata

        Raises:
            ValueError: If html_content or current_url is empty
        """
        pass
