"""Factory functions for creating test entities."""

from datetime import date, datetime
from typing import Any

from src.domain.entities.conference import Conference
from src.domain.entities.conversation import Conversation
from src.domain.entities.extracted_conference_member import ExtractedConferenceMember
from src.domain.entities.extracted_politician import ExtractedPolitician
from src.domain.entities.extracted_proposal_judge import ExtractedProposalJudge
from src.domain.entities.governing_body import GoverningBody
from src.domain.entities.meeting import Meeting
from src.domain.entities.minutes import Minutes
from src.domain.entities.parliamentary_group import ParliamentaryGroup
from src.domain.entities.political_party import PoliticalParty
from src.domain.entities.politician import Politician
from src.domain.entities.politician_affiliation import PoliticianAffiliation
from src.domain.entities.speaker import Speaker


def create_governing_body(**kwargs: Any) -> GoverningBody:
    """Create a test governing body."""
    defaults = {
        "id": 1,
        "name": "東京都",
        "type": "都道府県",
        "organization_code": "130001",
        "organization_type": "prefecture",
    }
    defaults.update(kwargs)
    return GoverningBody(**defaults)


def create_conference(**kwargs: Any) -> Conference:
    """Create a test conference."""
    defaults = {
        "id": 1,
        "governing_body_id": 1,
        "name": "議会全体",
        "description": "議会全体会議",
        "is_active": True,
        "members_introduction_url": None,
    }
    defaults.update(kwargs)
    return Conference(**defaults)


def create_meeting(**kwargs: Any) -> Meeting:
    """Create a test meeting."""
    defaults = {
        "id": 1,
        "conference_id": 1,
        "date": date(2023, 1, 1),
        "name": "定例会",
        "url": "https://example.com/meeting.pdf",
        "gcs_pdf_uri": None,
        "gcs_text_uri": None,
    }
    defaults.update(kwargs)
    return Meeting(**defaults)


def create_minutes(**kwargs: Any) -> Minutes:
    """Create a test minutes."""
    defaults = {
        "id": 1,
        "meeting_id": 1,
        "url": "https://example.com/minutes.pdf",
        "processed_at": None,
    }
    defaults.update(kwargs)
    return Minutes(**defaults)


def create_speaker(**kwargs: Any) -> Speaker:
    """Create a test speaker."""
    defaults = {
        "id": 1,
        "name": "山田太郎",
        "type": "議員",
        "is_politician": True,
        "political_party_name": None,
        "position": None,
    }
    defaults.update(kwargs)
    return Speaker(**defaults)


def create_politician(**kwargs: Any) -> Politician:
    """Create a test politician."""
    defaults = {
        "id": 1,
        "name": "山田太郎",
        "speaker_id": 1,
        "political_party_id": None,
        "furigana": None,
        "position": None,
        "district": None,
        "profile_image_url": None,
        "profile_page_url": None,
    }
    defaults.update(kwargs)
    return Politician(**defaults)


def create_extracted_politician(**kwargs: Any) -> ExtractedPolitician:
    """Create a test extracted politician."""
    defaults = {
        "id": 1,
        "name": "山田太郎",
        "party_id": 1,
        "district": "東京1区",
        "position": "衆議院議員",
        "profile_url": "https://example.com/profile",
        "image_url": "https://example.com/image.jpg",
        "status": "pending",
        "extracted_at": datetime.now(),
        "reviewed_at": None,
        "reviewer_id": None,
    }
    defaults.update(kwargs)
    return ExtractedPolitician(**defaults)


def create_political_party(**kwargs: Any) -> PoliticalParty:
    """Create a test political party."""
    defaults = {
        "id": 1,
        "name": "自由民主党",
        "short_name": "自民党",
        "members_list_url": None,
    }
    defaults.update(kwargs)
    return PoliticalParty(**defaults)


def create_conversation(**kwargs: Any) -> Conversation:
    """Create a test conversation."""
    defaults = {
        "id": 1,
        "comment": "これはテスト発言です。",
        "sequence_number": 1,
        "minutes_id": 1,
        "speaker_id": None,
        "speaker_name": "山田太郎",
        "chapter_number": 1,
        "sub_chapter_number": None,
    }
    defaults.update(kwargs)
    return Conversation(**defaults)


def create_parliamentary_group(**kwargs: Any) -> ParliamentaryGroup:
    """Create a test parliamentary group."""
    defaults = {
        "id": 1,
        "name": "自民党議員団",
        "conference_id": 1,
        "description": None,
        "is_active": True,
    }
    defaults.update(kwargs)
    return ParliamentaryGroup(**defaults)


def create_extracted_conference_member(**kwargs: Any) -> ExtractedConferenceMember:
    """Create a test extracted conference member."""
    defaults = {
        "id": 1,
        "conference_id": 1,
        "extracted_name": "山田太郎",
        "source_url": "https://example.com/members",
        "extracted_role": "議員",
        "extracted_party_name": "自由民主党",
        "extracted_at": datetime.now(),
        "matched_politician_id": None,
        "matching_confidence": None,
        "matching_status": "pending",
        "matched_at": None,
        "additional_data": None,
    }
    defaults.update(kwargs)
    return ExtractedConferenceMember(**defaults)


def create_politician_affiliation(**kwargs: Any) -> PoliticianAffiliation:
    """Create a test politician affiliation."""
    defaults = {
        "id": 1,
        "politician_id": 1,
        "conference_id": 1,
        "start_date": date(2023, 1, 1),
        "end_date": None,
        "role": "議員",
    }
    defaults.update(kwargs)
    return PoliticianAffiliation(**defaults)


def create_extracted_proposal_judge(**kwargs: Any) -> ExtractedProposalJudge:
    """Create a test extracted proposal judge."""
    defaults = {
        "id": 1,
        "proposal_id": 1,
        "extracted_politician_name": "山田太郎",
        "extracted_party_name": "自由民主党",
        "extracted_parliamentary_group_name": None,
        "extracted_judgment": "賛成",
        "source_url": "https://example.com/proposal/1",
        "extracted_at": datetime.now(),
        "matched_politician_id": None,
        "matched_parliamentary_group_id": None,
        "matching_confidence": None,
        "matching_status": "pending",
        "matched_at": None,
        "additional_data": None,
    }
    defaults.update(kwargs)
    return ExtractedProposalJudge(**defaults)
