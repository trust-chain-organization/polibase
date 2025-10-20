"""Tests for LinkAnalysisDomainService."""

import pytest

from src.domain.services.link_analysis_domain_service import LinkAnalysisDomainService
from src.domain.value_objects.link import Link


class TestLinkAnalysisDomainService:
    """Test cases for LinkAnalysisDomainService."""

    @pytest.fixture
    def service(self):
        """Create a LinkAnalysisDomainService instance."""
        return LinkAnalysisDomainService()

    def test_is_child_page_deeper_hierarchy(self, service):
        """Test child page detection for deeper hierarchy."""
        parent = "https://example.com/party/members"
        child = "https://example.com/party/members/tokyo"

        assert service.is_child_page(child, parent)

    def test_is_child_page_not_child(self, service):
        """Test that non-child pages are correctly identified."""
        current = "https://example.com/party/members"
        sibling = "https://example.com/party/about"

        assert not service.is_child_page(sibling, current)

    def test_is_child_page_parent(self, service):
        """Test that parent pages are not identified as children."""
        current = "https://example.com/party/members"
        parent = "https://example.com/party"

        assert not service.is_child_page(parent, current)

    def test_is_child_page_same_page(self, service):
        """Test that same page is not identified as child."""
        url = "https://example.com/party/members"

        assert not service.is_child_page(url, url)

    def test_is_sibling_page_different_query(self, service):
        """Test sibling detection with different query params."""
        ref = "https://example.com/members?page=1"
        sibling = "https://example.com/members?page=2"

        assert service.is_sibling_page(sibling, ref)

    def test_is_sibling_page_different_last_segment(self, service):
        """Test sibling detection with different last path segment."""
        ref = "https://example.com/members/tokyo"
        sibling = "https://example.com/members/osaka"

        assert service.is_sibling_page(sibling, ref)

    def test_is_sibling_page_not_sibling(self, service):
        """Test that non-siblings are correctly identified."""
        ref = "https://example.com/party/members"
        not_sibling = "https://example.com/party/members/tokyo"

        assert not service.is_sibling_page(not_sibling, ref)

    def test_is_same_domain_or_subdomain_same(self, service):
        """Test same domain detection."""
        url1 = "https://example.com/page1"
        url2 = "https://example.com/page2"

        assert service.is_same_domain_or_subdomain(url1, url2)

    def test_is_same_domain_or_subdomain_subdomain(self, service):
        """Test subdomain detection."""
        main = "https://example.com"
        sub = "https://sub.example.com/page"

        assert service.is_same_domain_or_subdomain(sub, main)

    def test_is_same_domain_or_subdomain_different(self, service):
        """Test different domain detection."""
        url1 = "https://example.com/page"
        url2 = "https://other.com/page"

        assert not service.is_same_domain_or_subdomain(url1, url2)

    def test_filter_child_pages(self, service):
        """Test filtering for child pages."""
        parent_url = "https://example.com/party/members"
        links = [
            Link(url="https://example.com/party/members/tokyo", text="Tokyo"),
            Link(url="https://example.com/party/members/osaka", text="Osaka"),
            Link(url="https://example.com/party/about", text="About"),
            Link(url="https://example.com/party", text="Home"),
        ]

        child_links = service.filter_child_pages(links, parent_url)

        assert len(child_links) == 2
        urls = [link.url for link in child_links]
        assert "https://example.com/party/members/tokyo" in urls
        assert "https://example.com/party/members/osaka" in urls

    def test_filter_sibling_pages(self, service):
        """Test filtering for sibling pages."""
        reference_url = "https://example.com/members?page=1"
        links = [
            Link(url="https://example.com/members?page=1", text="Page 1"),
            Link(url="https://example.com/members?page=2", text="Page 2"),
            Link(url="https://example.com/members?page=3", text="Page 3"),
            Link(url="https://example.com/members/tokyo", text="Tokyo"),
        ]

        sibling_links = service.filter_sibling_pages(links, reference_url)

        assert len(sibling_links) == 2
        urls = [link.url for link in sibling_links]
        assert "https://example.com/members?page=2" in urls
        assert "https://example.com/members?page=3" in urls

    def test_exclude_current_page(self, service):
        """Test excluding current page from list."""
        current_url = "https://example.com/members"
        links = [
            Link(url="https://example.com/members", text="Current"),
            Link(url="https://example.com/members/tokyo", text="Tokyo"),
            Link(url="https://example.com/members/osaka", text="Osaka"),
        ]

        filtered_links = service.exclude_current_page(links, current_url)

        assert len(filtered_links) == 2
        urls = [link.url for link in filtered_links]
        assert current_url not in urls


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
