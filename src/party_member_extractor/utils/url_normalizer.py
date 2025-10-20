"""URL normalization utility for consistent URL comparison and deduplication.

This module provides URL normalization functionality to ensure consistent
URL comparison across the party member scraping system. It handles common
variations like trailing slashes, fragments, and case differences in
scheme/host components.
"""

from urllib.parse import urlparse, urlunparse


def normalize_url(url: str) -> str:
    """Normalize URL for consistent comparison and deduplication.

    This function standardizes URLs by:
    - Converting scheme and netloc (host) to lowercase
    - Removing URL fragments (#...)
    - Removing trailing slashes from paths (except for root path "/")
    - Preserving query parameters and path parameters

    Args:
        url: Raw URL string to normalize

    Returns:
        Normalized URL string

    Raises:
        ValueError: If URL is empty, whitespace-only, or has invalid format

    Examples:
        >>> normalize_url("HTTP://Example.COM/path/")
        'http://example.com/path'

        >>> normalize_url("https://example.com/page#section")
        'https://example.com/page'

        >>> normalize_url("https://example.com/")
        'https://example.com/'

        >>> normalize_url("https://example.com?q=test")
        'https://example.com?q=test'
    """
    if not url or not url.strip():
        raise ValueError("URL cannot be empty or whitespace")

    url = url.strip()

    try:
        parsed = urlparse(url)

        # Ensure scheme and netloc exist
        if not parsed.scheme or not parsed.netloc:
            raise ValueError(f"Invalid URL format: {url}")

        # Normalize: lowercase scheme/netloc, remove fragment/trailing slash
        normalized = urlunparse(
            (
                parsed.scheme.lower(),
                parsed.netloc.lower(),
                parsed.path.rstrip("/") if parsed.path != "/" else "/",
                parsed.params,
                parsed.query,
                "",  # Remove fragment
            )
        )

        return normalized

    except Exception as e:
        raise ValueError(f"Failed to normalize URL '{url}': {e}") from e
