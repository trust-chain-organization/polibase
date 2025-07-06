"""Data Transfer Object type definitions."""

from datetime import date, datetime
from typing import TypedDict


class GoverningBodyDTO(TypedDict):
    """Governing body data transfer object."""

    id: int
    name: str
    type: str
    organization_code: str | None
    organization_type: str | None
    created_at: datetime
    updated_at: datetime


class ConferenceDTO(TypedDict):
    """Conference data transfer object."""

    id: int
    governing_body_id: int
    name: str
    description: str | None
    members_introduction_url: str | None
    created_at: datetime
    updated_at: datetime


class PoliticianDTO(TypedDict):
    """Politician data transfer object."""

    id: int
    name: str
    party_id: int | None
    prefecture: str | None
    electoral_district: str | None
    profile_url: str | None
    image_url: str | None
    created_at: datetime
    updated_at: datetime


class SpeakerDTO(TypedDict):
    """Speaker data transfer object."""

    id: int
    name: str
    normalized_name: str
    is_politician: bool
    meeting_id: int | None
    politician_id: int | None
    party_affiliation: str | None
    position_or_title: str | None
    created_at: datetime
    updated_at: datetime


class MeetingDTO(TypedDict):
    """Meeting data transfer object."""

    id: int
    governing_body_id: int
    conference_id: int
    date: date
    name: str
    url: str | None
    pdf_url: str | None
    gcs_pdf_uri: str | None
    gcs_text_uri: str | None
    created_at: datetime
    updated_at: datetime


class ConversationDTO(TypedDict):
    """Conversation data transfer object."""

    id: int
    speaker_id: int
    meeting_id: int
    sequence_number: int
    content: str
    created_at: datetime
    updated_at: datetime


class MinutesDTO(TypedDict):
    """Minutes data transfer object."""

    id: int
    meeting_id: int
    content: str
    created_at: datetime
    updated_at: datetime


class ParliamentaryGroupDTO(TypedDict):
    """Parliamentary group data transfer object."""

    id: int
    conference_id: int
    name: str
    abbreviated_name: str | None
    political_party_id: int | None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class ExtractedConferenceMemberDTO(TypedDict):
    """Extracted conference member data transfer object."""

    id: int
    conference_id: int
    name: str
    party_affiliation: str | None
    role: str | None
    matching_status: str
    matched_politician_id: int | None
    confidence_score: float | None
    created_at: datetime
    updated_at: datetime
