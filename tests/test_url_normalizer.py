"""Unit tests for URL normalization utility."""

import pytest

from src.domain.entities.party_scraping_state import PartyScrapingState


class TestNormalizeUrl:
    """Test cases for normalize_url function."""

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
        """Test that URL fragments are removed."""
        url = "https://example.com/path#section"
        result = PartyScrapingState.normalize_url(url)
        assert result == "https://example.com/path"

    def test_normalize_lowercase_scheme(self) -> None:
        """Test that scheme is converted to lowercase."""
        url = "HTTP://example.com/path"
        result = PartyScrapingState.normalize_url(url)
        assert result == "http://example.com/path"

    def test_normalize_lowercase_host(self) -> None:
        """Test that host is converted to lowercase."""
        url = "https://Example.COM/path"
        result = PartyScrapingState.normalize_url(url)
        assert result == "https://example.com/path"

    def test_normalize_preserves_query_params(self) -> None:
        """Test that query parameters are preserved."""
        url = "https://example.com/path?q=test&page=1"
        result = PartyScrapingState.normalize_url(url)
        assert result == "https://example.com/path?q=test&page=1"

    def test_normalize_complex_url(self) -> None:
        """Test normalization of complex URL with multiple components."""
        url = "HTTPS://Example.COM/Path/To/Page/?query=test#section"
        result = PartyScrapingState.normalize_url(url)
        # Note: Path is case-sensitive and preserved, only scheme/host are lowercased
        assert result == "https://example.com/Path/To/Page?query=test"

    def test_normalize_removes_fragment_with_query(self) -> None:
        """Test fragment removal when query params are present."""
        url = "https://example.com/path?q=test#fragment"
        result = PartyScrapingState.normalize_url(url)
        assert result == "https://example.com/path?q=test"

    def test_normalize_multiple_trailing_slashes(self) -> None:
        """Test that multiple trailing slashes are removed."""
        url = "https://example.com/path///"
        result = PartyScrapingState.normalize_url(url)
        assert result == "https://example.com/path"

    def test_normalize_empty_url_raises_error(self) -> None:
        """Test that empty URL raises ValueError."""
        with pytest.raises(ValueError, match="URL cannot be empty"):
            PartyScrapingState.normalize_url("")

    def test_normalize_whitespace_only_url_raises_error(self) -> None:
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

    def test_normalize_strips_whitespace(self) -> None:
        """Test that leading/trailing whitespace is stripped."""
        url = "  https://example.com/path  "
        result = PartyScrapingState.normalize_url(url)
        assert result == "https://example.com/path"

    def test_normalize_idempotent(self) -> None:
        """Test that normalizing twice produces same result."""
        url = "HTTPS://Example.COM/Path/#section"
        first = PartyScrapingState.normalize_url(url)
        second = PartyScrapingState.normalize_url(first)
        assert first == second

    def test_normalize_with_port(self) -> None:
        """Test normalization preserves port number."""
        url = "https://example.com:8080/path"
        result = PartyScrapingState.normalize_url(url)
        assert result == "https://example.com:8080/path"

    def test_normalize_with_subdomain(self) -> None:
        """Test normalization with subdomain."""
        url = "https://www.example.com/path"
        result = PartyScrapingState.normalize_url(url)
        assert result == "https://www.example.com/path"

    def test_normalize_japanese_path(self) -> None:
        """Test normalization with Japanese characters in path."""
        url = "https://example.com/議員リスト"
        result = PartyScrapingState.normalize_url(url)
        assert "example.com" in result
        assert "議員リスト" in result

    def test_normalize_path_params(self) -> None:
        """Test that path parameters are preserved."""
        url = "https://example.com/path;param=value"
        result = PartyScrapingState.normalize_url(url)
        assert ";param=value" in result


class TestUrlNormalizerEdgeCases:
    """Test edge cases and special scenarios for URL normalization."""

    def test_normalize_very_long_url(self) -> None:
        """Test normalization of very long URL."""
        path = "/".join([f"segment{i}" for i in range(100)])
        url = f"https://example.com/{path}"
        result = PartyScrapingState.normalize_url(url)
        assert result.startswith("https://example.com/")
        assert result.endswith("segment99")

    def test_normalize_url_with_special_chars_in_query(self) -> None:
        """Test URL with special characters in query string."""
        url = "https://example.com/path?name=田中太郎&age=30"
        result = PartyScrapingState.normalize_url(url)
        assert "example.com" in result
        assert "田中太郎" in result

    def test_normalize_different_schemes(self) -> None:
        """Test normalization with different URL schemes."""
        http_url = "http://example.com/path"
        https_url = "https://example.com/path"

        http_result = PartyScrapingState.normalize_url(http_url)
        https_result = PartyScrapingState.normalize_url(https_url)

        assert http_result == "http://example.com/path"
        assert https_result == "https://example.com/path"
        assert http_result != https_result

    def test_normalize_ip_address(self) -> None:
        """Test normalization with IP address."""
        url = "http://192.168.1.1/path"
        result = PartyScrapingState.normalize_url(url)
        assert result == "http://192.168.1.1/path"

    def test_normalize_localhost(self) -> None:
        """Test normalization with localhost."""
        url = "http://localhost:3000/path"
        result = PartyScrapingState.normalize_url(url)
        assert result == "http://localhost:3000/path"

    def test_normalize_url_deduplication_use_case(self) -> None:
        """Test that variations of same URL normalize to same result."""
        variations = [
            "https://example.com/path",
            "HTTPS://example.com/path",
            "https://EXAMPLE.com/path",
            "https://example.com/path/",
            "https://example.com/path#section",
            "https://example.com/path/#section",
        ]

        results = [PartyScrapingState.normalize_url(url) for url in variations]

        # All should normalize to the same result
        assert all(r == "https://example.com/path" for r in results)
