"""Configuration value object for hierarchical scraping."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ScrapingConfig:
    """Configuration for hierarchical scraping.

    This value object encapsulates all configuration parameters for
    hierarchical party member scraping operations.

    Attributes:
        max_depth: Maximum navigation depth (0=top page only)
        recursion_limit: LangGraph recursion limit for state machine
        min_confidence_threshold: Minimum confidence for link classification
        max_pages: Maximum number of pages to visit (safety limit)
    """

    max_depth: int = 2
    recursion_limit: int = 100  # Conservative default
    min_confidence_threshold: float = 0.7
    max_pages: int = 1000  # Safety limit

    def __post_init__(self) -> None:
        """Validate configuration values.

        Raises:
            ValueError: If any configuration value is invalid
        """
        if self.max_depth < 0:
            raise ValueError("max_depth must be >= 0")
        if self.recursion_limit < 10:
            raise ValueError("recursion_limit must be >= 10")
        if not 0.0 <= self.min_confidence_threshold <= 1.0:
            raise ValueError("min_confidence_threshold must be between 0.0 and 1.0")
        if self.max_pages < 1:
            raise ValueError("max_pages must be >= 1")

    @classmethod
    def for_large_party(cls) -> "ScrapingConfig":
        """Configuration for large parties (e.g., JCP with 47 prefectures).

        Large parties typically have:
        - Deep hierarchical structure (prefecture → city → members)
        - Many pages to navigate
        - High recursion requirements

        Returns:
            ScrapingConfig optimized for large parties
        """
        return cls(
            max_depth=3,
            recursion_limit=500,
            min_confidence_threshold=0.7,
            max_pages=2000,
        )

    @classmethod
    def for_small_party(cls) -> "ScrapingConfig":
        """Configuration for small parties.

        Small parties typically have:
        - Flat or shallow structure
        - Fewer pages to navigate
        - Lower recursion requirements

        Returns:
            ScrapingConfig optimized for small parties
        """
        return cls(
            max_depth=2,
            recursion_limit=50,
            min_confidence_threshold=0.7,
            max_pages=200,
        )

    @classmethod
    def for_testing(cls) -> "ScrapingConfig":
        """Configuration for testing (limits API calls).

        Test configuration has:
        - Minimal depth to reduce API usage
        - Low recursion limit
        - Lower confidence threshold for broader testing
        - Strict page limit

        Returns:
            ScrapingConfig optimized for testing
        """
        return cls(
            max_depth=1,
            recursion_limit=10,
            min_confidence_threshold=0.5,
            max_pages=10,
        )
