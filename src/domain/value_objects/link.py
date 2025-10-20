"""Link value object for representing web links."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Link:
    """Value object representing a web link.

    This is an immutable value object that represents a link extracted from HTML.
    It contains all relevant metadata about the link.

    Attributes:
        url: The absolute URL of the link
        text: The visible text of the link
        rel: The rel attribute value (e.g., "nofollow", "next")
        title: The title attribute value
    """

    url: str
    text: str
    rel: str = ""
    title: str = ""

    def __post_init__(self) -> None:
        """Validate the link data."""
        if not self.url:
            raise ValueError("URL cannot be empty")
        if not isinstance(self.url, str):
            raise TypeError("URL must be a string")
