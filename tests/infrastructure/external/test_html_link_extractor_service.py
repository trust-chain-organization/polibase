"""Tests for BeautifulSoupLinkExtractor."""

import pytest

from src.infrastructure.external.html_link_extractor_service import (
    BeautifulSoupLinkExtractor,
)


class TestBeautifulSoupLinkExtractor:
    """Test cases for BeautifulSoupLinkExtractor."""

    @pytest.fixture
    def extractor(self):
        """Create a BeautifulSoupLinkExtractor instance."""
        return BeautifulSoupLinkExtractor()

    def test_extract_links_basic(self, extractor):
        """Test basic link extraction from HTML."""
        html = """
        <html>
            <body>
                <a href="/members">議員一覧</a>
                <a href="/about">About</a>
                <a href="https://example.com/profile/1">Profile 1</a>
            </body>
        </html>
        """
        base_url = "https://example.com"

        links = extractor.extract_links(html, base_url)

        assert len(links) == 3
        assert any(link.url == "https://example.com/members" for link in links)
        assert any(link.url == "https://example.com/about" for link in links)
        assert any(link.url == "https://example.com/profile/1" for link in links)

    def test_extract_links_with_text_and_title(self, extractor):
        """Test link extraction includes text and title attributes."""
        html = """
        <html>
            <body>
                <a href="/members" title="Member List">議員一覧</a>
            </body>
        </html>
        """
        base_url = "https://example.com"

        links = extractor.extract_links(html, base_url)

        assert len(links) == 1
        assert links[0].text == "議員一覧"
        assert links[0].title == "Member List"
        assert links[0].url == "https://example.com/members"

    def test_extract_links_skips_invalid_links(self, extractor):
        """Test that invalid links are skipped."""
        html = """
        <html>
            <body>
                <a href="#">Anchor</a>
                <a href="javascript:void(0)">JavaScript</a>
                <a href="mailto:test@example.com">Email</a>
                <a href="tel:123-456-7890">Phone</a>
                <a href="/valid">Valid Link</a>
            </body>
        </html>
        """
        base_url = "https://example.com"

        links = extractor.extract_links(html, base_url)

        # Only the valid link should be extracted
        assert len(links) == 1
        assert links[0].url == "https://example.com/valid"

    def test_extract_links_resolves_relative_urls(self, extractor):
        """Test that relative URLs are resolved to absolute URLs."""
        html = """
        <html>
            <body>
                <a href="../members">Members</a>
                <a href="./about">About</a>
                <a href="contact">Contact</a>
            </body>
        </html>
        """
        base_url = "https://example.com/party/info"

        links = extractor.extract_links(html, base_url)

        assert len(links) == 3
        # ../members from /party/info resolves to /members
        assert any(link.url == "https://example.com/members" for link in links)
        # ./about from /party/info resolves to /party/about
        assert any(link.url == "https://example.com/party/about" for link in links)
        # contact from /party/info resolves to /party/contact
        assert any(link.url == "https://example.com/party/contact" for link in links)

    def test_extract_links_empty_html_raises_error(self, extractor):
        """Test that empty HTML raises ValueError."""
        with pytest.raises(ValueError, match="HTML content cannot be empty"):
            extractor.extract_links("", "https://example.com")

    def test_extract_links_empty_base_url_raises_error(self, extractor):
        """Test that empty base URL raises ValueError."""
        html = "<html><body><a href='/test'>Test</a></body></html>"
        with pytest.raises(ValueError, match="Base URL cannot be empty"):
            extractor.extract_links(html, "")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
