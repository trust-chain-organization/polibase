"""Politician-related DTOs."""

from dataclasses import dataclass


@dataclass
class CreatePoliticianDTO:
    """DTO for creating a politician."""

    name: str
    political_party_id: int | None = None
    furigana: str | None = None
    district: str | None = None
    profile_page_url: str | None = None
    party_position: str | None = None


@dataclass
class UpdatePoliticianDTO:
    """DTO for updating a politician."""

    id: int
    name: str | None = None
    political_party_id: int | None = None
    furigana: str | None = None
    district: str | None = None
    profile_page_url: str | None = None
    party_position: str | None = None


@dataclass
class PoliticianDTO:
    """DTO for politician data."""

    id: int
    name: str
    political_party_id: int | None
    political_party_name: str | None
    furigana: str | None
    district: str | None
    profile_page_url: str | None
    party_position: str | None = None


@dataclass
class PoliticianPartyExtractedPoliticianDTO:
    """DTO for politician data extracted from party websites."""

    name: str
    party_id: int
    furigana: str | None = None
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
class PoliticianPartyExtractedPoliticianOutputDTO:
    """DTO for politician extracted from party websites output."""

    id: int
    name: str
    party_id: int | None
    party_name: str | None
    district: str | None
    profile_url: str | None
    status: str
