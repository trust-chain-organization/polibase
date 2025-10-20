"""Tests for link detection tool."""

import pytest

from src.party_member_extractor.tools.link_detector import (
    LinkDetector,
    detect_child_page_links,
)


class TestLinkDetector:
    """Test cases for LinkDetector class."""

    def test_extract_links_basic(self):
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

        detector = LinkDetector()
        links = detector.extract_links(html, base_url)

        assert len(links) == 3
        assert any(link["url"] == "https://example.com/members" for link in links)
        assert any(link["url"] == "https://example.com/about" for link in links)
        assert any(link["url"] == "https://example.com/profile/1" for link in links)

    def test_extract_links_with_text_and_title(self):
        """Test link extraction includes text and title attributes."""
        html = """
        <html>
            <body>
                <a href="/members" title="Member List">議員一覧</a>
            </body>
        </html>
        """
        base_url = "https://example.com"

        detector = LinkDetector()
        links = detector.extract_links(html, base_url)

        assert len(links) == 1
        assert links[0]["text"] == "議員一覧"
        assert links[0]["title"] == "Member List"
        assert links[0]["url"] == "https://example.com/members"

    def test_extract_links_skips_invalid_links(self):
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

        detector = LinkDetector()
        links = detector.extract_links(html, base_url)

        # Only the valid link should be extracted
        assert len(links) == 1
        assert links[0]["url"] == "https://example.com/valid"

    def test_extract_links_resolves_relative_urls(self):
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

        detector = LinkDetector()
        links = detector.extract_links(html, base_url)

        assert len(links) == 3
        # ../members from /party/info resolves to /members
        assert any(link["url"] == "https://example.com/members" for link in links)
        # ./about from /party/info resolves to /party/about
        assert any(link["url"] == "https://example.com/party/about" for link in links)
        # contact from /party/info resolves to /party/contact
        assert any(link["url"] == "https://example.com/party/contact" for link in links)

    def test_extract_links_filters_external_domains(self):
        """Test that links to external domains are filtered out."""
        html = """
        <html>
            <body>
                <a href="https://example.com/members">Internal</a>
                <a href="https://external.com/page">External</a>
                <a href="https://sub.example.com/page">Subdomain</a>
            </body>
        </html>
        """
        base_url = "https://example.com"

        detector = LinkDetector()
        links = detector.extract_links(html, base_url)

        # Should include internal and subdomain, but not external
        assert len(links) == 2
        urls = [link["url"] for link in links]
        assert "https://example.com/members" in urls
        assert "https://sub.example.com/page" in urls
        assert "https://external.com/page" not in urls

    def test_is_same_domain_or_subdomain(self):
        """Test domain/subdomain checking logic."""
        detector = LinkDetector()

        # Same domain
        assert detector._is_same_domain_or_subdomain(
            "https://example.com/page", "https://example.com"
        )

        # Subdomain
        assert detector._is_same_domain_or_subdomain(
            "https://sub.example.com/page", "https://example.com"
        )

        # Different domain
        assert not detector._is_same_domain_or_subdomain(
            "https://other.com/page", "https://example.com"
        )

        # Different TLD
        assert not detector._is_same_domain_or_subdomain(
            "https://example.org/page", "https://example.com"
        )

    def test_filter_child_page_links_deeper_hierarchy(self):
        """Test filtering for child pages (deeper in hierarchy)."""
        links = [
            {"url": "https://example.com/party/members"},
            {"url": "https://example.com/party/members/tokyo"},
            {"url": "https://example.com/party/members/osaka"},
            {"url": "https://example.com/party"},  # Parent
            {"url": "https://example.com/about"},  # Different branch
        ]
        current_url = "https://example.com/party/members"

        detector = LinkDetector()
        child_links = detector.filter_child_page_links(links, current_url)

        # Should only include deeper pages
        assert len(child_links) == 2
        urls = [link["url"] for link in child_links]
        assert "https://example.com/party/members/tokyo" in urls
        assert "https://example.com/party/members/osaka" in urls

    def test_filter_child_page_links_same_level_with_query(self):
        """Test filtering includes same level pages with different query params."""
        links = [
            {"url": "https://example.com/members?page=1"},
            {"url": "https://example.com/members?page=2"},
            {"url": "https://example.com/members?page=3"},
        ]
        current_url = "https://example.com/members?page=1"

        detector = LinkDetector()
        child_links = detector.filter_child_page_links(links, current_url)

        # Should include pages with different query params
        assert len(child_links) == 2
        urls = [link["url"] for link in child_links]
        assert "https://example.com/members?page=2" in urls
        assert "https://example.com/members?page=3" in urls

    def test_filter_child_page_links_excludes_current_page(self):
        """Test that current page URL is excluded."""
        links = [
            {"url": "https://example.com/members"},
            {"url": "https://example.com/members/tokyo"},
        ]
        current_url = "https://example.com/members"

        detector = LinkDetector()
        child_links = detector.filter_child_page_links(links, current_url)

        # Should only include child, not current
        assert len(child_links) == 1
        assert child_links[0]["url"] == "https://example.com/members/tokyo"


class TestDetectChildPageLinksTool:
    """Test cases for the detect_child_page_links tool."""

    def test_detect_child_page_links_basic(self):
        """Test the tool function with basic HTML."""
        html = """
        <html>
            <body>
                <a href="/members/tokyo">東京都</a>
                <a href="/members/osaka">大阪府</a>
            </body>
        </html>
        """
        current_url = "https://example.com/members"

        result = detect_child_page_links.invoke(
            {"html_content": html, "current_url": current_url}
        )

        assert "detected_links" in result
        assert "count" in result
        assert "current_url" in result

        assert result["count"] == 2
        assert result["current_url"] == current_url

        # Check that links are properly formatted
        links = result["detected_links"]
        assert len(links) == 2
        assert all("url" in link for link in links)
        assert all("text" in link for link in links)

    def test_detect_child_page_links_empty_html(self):
        """Test with HTML containing no links."""
        html = "<html><body><p>No links here</p></body></html>"
        current_url = "https://example.com/page"

        result = detect_child_page_links.invoke(
            {"html_content": html, "current_url": current_url}
        )

        assert result["count"] == 0
        assert len(result["detected_links"]) == 0

    def test_detect_child_page_links_filters_correctly(self):
        """Test that the tool correctly filters for child pages only."""
        html = """
        <html>
            <body>
                <a href="/party">党ホーム</a>
                <a href="/party/members">議員一覧</a>
                <a href="/party/members/tokyo">東京都</a>
                <a href="https://external.com">外部リンク</a>
            </body>
        </html>
        """
        current_url = "https://example.com/party/members"

        result = detect_child_page_links.invoke(
            {"html_content": html, "current_url": current_url}
        )

        # Should only include the tokyo page (child of current)
        assert result["count"] == 1
        assert result["detected_links"][0]["url"] == (
            "https://example.com/party/members/tokyo"
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
