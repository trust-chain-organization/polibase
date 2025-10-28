"""Tests for ScrapingConfig value object."""

import pytest

from src.domain.value_objects.scraping_config import ScrapingConfig


class TestScrapingConfigDefaults:
    """Test default configuration values."""

    def test_default_values(self) -> None:
        """Test that default values are correctly set."""
        config = ScrapingConfig()

        assert config.max_depth == 2
        assert config.recursion_limit == 100
        assert config.min_confidence_threshold == 0.7
        assert config.max_pages == 1000


class TestScrapingConfigValidation:
    """Test configuration validation."""

    def test_negative_max_depth_raises_error(self) -> None:
        """Test that negative max_depth raises ValueError."""
        with pytest.raises(ValueError, match="max_depth must be >= 0"):
            ScrapingConfig(max_depth=-1)

    def test_too_small_recursion_limit_raises_error(self) -> None:
        """Test that recursion_limit < 10 raises ValueError."""
        with pytest.raises(ValueError, match="recursion_limit must be >= 10"):
            ScrapingConfig(recursion_limit=5)

    def test_min_confidence_threshold_below_zero_raises_error(self) -> None:
        """Test that min_confidence_threshold < 0 raises ValueError."""
        with pytest.raises(
            ValueError, match="min_confidence_threshold must be between 0.0 and 1.0"
        ):
            ScrapingConfig(min_confidence_threshold=-0.1)

    def test_min_confidence_threshold_above_one_raises_error(self) -> None:
        """Test that min_confidence_threshold > 1 raises ValueError."""
        with pytest.raises(
            ValueError, match="min_confidence_threshold must be between 0.0 and 1.0"
        ):
            ScrapingConfig(min_confidence_threshold=1.1)

    def test_zero_max_pages_raises_error(self) -> None:
        """Test that max_pages < 1 raises ValueError."""
        with pytest.raises(ValueError, match="max_pages must be >= 1"):
            ScrapingConfig(max_pages=0)

    def test_valid_edge_case_values(self) -> None:
        """Test that edge case values are accepted."""
        # These should not raise any errors
        config = ScrapingConfig(
            max_depth=0,
            recursion_limit=10,
            min_confidence_threshold=0.0,
            max_pages=1,
        )
        assert config.max_depth == 0
        assert config.recursion_limit == 10
        assert config.min_confidence_threshold == 0.0
        assert config.max_pages == 1

        config2 = ScrapingConfig(min_confidence_threshold=1.0)
        assert config2.min_confidence_threshold == 1.0


class TestScrapingConfigFactoryMethods:
    """Test factory methods for preset configurations."""

    def test_for_large_party(self) -> None:
        """Test large party configuration preset."""
        config = ScrapingConfig.for_large_party()

        assert config.max_depth == 3
        assert config.recursion_limit == 500
        assert config.min_confidence_threshold == 0.7
        assert config.max_pages == 2000

    def test_for_small_party(self) -> None:
        """Test small party configuration preset."""
        config = ScrapingConfig.for_small_party()

        assert config.max_depth == 2
        assert config.recursion_limit == 50
        assert config.min_confidence_threshold == 0.7
        assert config.max_pages == 200

    def test_for_testing(self) -> None:
        """Test testing configuration preset."""
        config = ScrapingConfig.for_testing()

        assert config.max_depth == 1
        assert config.recursion_limit == 10
        assert config.min_confidence_threshold == 0.5
        assert config.max_pages == 10


class TestScrapingConfigImmutability:
    """Test that ScrapingConfig is immutable."""

    def test_config_is_frozen(self) -> None:
        """Test that config cannot be modified after creation."""
        config = ScrapingConfig()

        with pytest.raises(AttributeError):
            config.max_depth = 5  # type: ignore[misc]

        with pytest.raises(AttributeError):
            config.recursion_limit = 200  # type: ignore[misc]
