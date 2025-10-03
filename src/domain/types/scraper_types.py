"""Type definitions for scraper services - Domain layer."""

from dataclasses import dataclass


@dataclass
class ScrapedProposal:
    """Data class for scraped proposal information."""

    url: str
    content: str
    proposal_number: str | None = None
    submission_date: str | None = None
    summary: str | None = None

    def to_dict(self) -> dict[str, str | None]:
        """Convert to dictionary for backward compatibility."""
        return {
            "url": self.url,
            "content": self.content,
            "proposal_number": self.proposal_number,
            "submission_date": self.submission_date,
            "summary": self.summary,
        }
