"""Politician-related DTOs."""

from dataclasses import dataclass


@dataclass
class CreatePoliticianDTO:
    """DTO for creating a politician."""

    name: str
    speaker_id: int
    political_party_id: int | None = None
    furigana: str | None = None
    position: str | None = None
    district: str | None = None
    profile_page_url: str | None = None


@dataclass
class UpdatePoliticianDTO:
    """DTO for updating a politician."""

    id: int
    name: str | None = None
    political_party_id: int | None = None
    furigana: str | None = None
    position: str | None = None
    district: str | None = None
    profile_page_url: str | None = None


@dataclass
class PoliticianDTO:
    """DTO for politician data."""

    id: int
    name: str
    speaker_id: int
    political_party_id: int | None
    political_party_name: str | None
    furigana: str | None
    position: str | None
    district: str | None
    profile_page_url: str | None


@dataclass
class ExtractedPoliticianDTO:
    """DTO for politician data extracted from web."""

    name: str
    party_id: int
    furigana: str | None = None
    position: str | None = None
    district: str | None = None
    profile_page_url: str | None = None
    source_url: str | None = None


@dataclass
class ScrapePoliticiansInputDTO:
    """DTO for scraping politicians request."""

    party_id: int | None = None
    all_parties: bool = False
    dry_run: bool = False


@dataclass
class ExtractedPoliticianOutputDTO:
    """DTO for extracted politician output."""

    id: int
    name: str
    party_id: int | None
    party_name: str | None
    district: str | None
    position: str | None
    profile_url: str | None
    status: str
