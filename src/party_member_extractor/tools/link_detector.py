"""Link detection tool for extracting child page links from HTML content."""

import logging
from typing import Any
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup
from langchain_core.tools import tool

logger = logging.getLogger(__name__)


class LinkDetector:
    """Detects and extracts links from HTML content."""

    def __init__(self):
        """Initialize the link detector."""
        pass

    def extract_links(self, html_content: str, base_url: str) -> list[dict[str, str]]:
        """
        Extract all links from HTML content.

        Args:
            html_content: HTML content to parse
            base_url: Base URL for resolving relative links

        Returns:
            List of dictionaries containing link information:
            [{"url": "...", "text": "...", "rel": "..."}]
        """
        soup = BeautifulSoup(html_content, "html.parser")
        links: list[dict[str, str]] = []

        for anchor in soup.find_all("a", href=True):
            href = anchor.get("href", "")  # type: ignore[assignment]
            if not href or href.startswith(("#", "javascript:", "mailto:", "tel:")):  # type: ignore[arg-type]
                # Skip empty, anchor, javascript, mailto, and tel links
                continue

            # Resolve relative URLs to absolute URLs
            absolute_url = urljoin(base_url, href)  # type: ignore[arg-type]

            # Extract link text (strip whitespace)
            text = anchor.get_text(strip=True)

            # Extract rel attribute if exists
            rel = anchor.get("rel", [])  # type: ignore[assignment,arg-type]
            rel_str = " ".join(rel) if isinstance(rel, list) else str(rel)  # type: ignore[arg-type]

            # Extract title attribute if exists
            title = anchor.get("title", "")  # type: ignore[assignment]

            # Only add if URL is different from base_url and is same domain or subdomain
            if absolute_url != base_url and self._is_same_domain_or_subdomain(
                absolute_url, base_url
            ):
                links.append(
                    {
                        "url": absolute_url,
                        "text": text,
                        "rel": rel_str,
                        "title": str(title),
                    }
                )

        return links

    def _is_same_domain_or_subdomain(self, url: str, base_url: str) -> bool:
        """
        Check if URL is same domain or subdomain as base URL.

        Args:
            url: URL to check
            base_url: Base URL to compare against

        Returns:
            True if same domain or subdomain, False otherwise
        """
        try:
            url_parts = urlparse(url)
            base_parts = urlparse(base_url)

            # Extract domains
            url_domain = url_parts.netloc.lower()
            base_domain = base_parts.netloc.lower()

            # Same domain
            if url_domain == base_domain:
                return True

            # Check if subdomain
            if url_domain.endswith("." + base_domain):
                return True

            # Check if base is subdomain of url (for reverse case)
            if base_domain.endswith("." + url_domain):
                return True

            return False
        except Exception as e:
            logger.warning(f"Error parsing URL {url}: {e}")
            return False

    def filter_child_page_links(
        self, links: list[dict[str, str]], current_url: str
    ) -> list[dict[str, str]]:
        """
        Filter links to only include potential child pages.

        Child pages are defined as:
        - Links that go deeper in the URL hierarchy
        - Links that are not to parent directories
        - Links that are not external

        Args:
            links: List of link dictionaries
            current_url: Current page URL

        Returns:
            Filtered list of child page links
        """
        current_parts = urlparse(current_url)
        current_path = current_parts.path.rstrip("/")
        current_path_segments = [s for s in current_path.split("/") if s]

        child_links: list[dict[str, str]] = []

        for link in links:
            link_parts = urlparse(link["url"])
            link_path = link_parts.path.rstrip("/")
            link_path_segments = [s for s in link_path.split("/") if s]

            # Skip if same page
            if link["url"] == current_url:
                continue

            # Check if link path starts with current path (is a child or same level)
            if len(link_path_segments) > len(current_path_segments):
                # Potentially a child page
                # Check if the beginning matches
                if link_path_segments[: len(current_path_segments)] == (
                    current_path_segments
                ):
                    child_links.append(link)
            elif len(link_path_segments) == len(current_path_segments):
                # Same level - might be a sibling page (e.g., page=2, page=3)
                # Include if query params differ or last segment differs
                if link_parts.query != current_parts.query or (
                    link_path_segments != current_path_segments
                ):
                    child_links.append(link)

        return child_links


@tool
def detect_child_page_links(html_content: str, current_url: str) -> dict[str, Any]:
    """
    Detect child page links from HTML content.

    This tool extracts links from HTML and filters for potential child pages
    that may contain member lists or related content.

    Args:
        html_content: HTML content of the page
        current_url: Current page URL for resolving relative links

    Returns:
        Dictionary containing:
        - detected_links: List of detected links with metadata
        - count: Number of links detected
        - current_url: The provided current URL
    """
    detector = LinkDetector()

    # Extract all links
    all_links = detector.extract_links(html_content, current_url)

    # Filter for child page links
    child_links = detector.filter_child_page_links(all_links, current_url)

    logger.info(
        f"Detected {len(child_links)} child page links "
        f"from {len(all_links)} total links"
    )

    return {
        "detected_links": child_links,
        "count": len(child_links),
        "current_url": current_url,
    }
