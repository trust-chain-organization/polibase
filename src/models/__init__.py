"""Database models using Pydantic for type safety"""

from .base import BaseModel
from .conference import Conference, ConferenceCreate, ConferenceUpdate
from .governing_body import GoverningBody, GoverningBodyCreate, GoverningBodyUpdate
from .meeting import Meeting, MeetingCreate, MeetingUpdate
from .parliamentary_group import (
    ParliamentaryGroup,
    ParliamentaryGroupCreate,
    ParliamentaryGroupMembership,
    ParliamentaryGroupMembershipCreate,
    ParliamentaryGroupUpdate,
)
from .political_party import PoliticalParty, PoliticalPartyCreate, PoliticalPartyUpdate
from .politician import Politician, PoliticianCreate, PoliticianUpdate
from .speaker import Speaker, SpeakerCreate, SpeakerUpdate

__all__ = [
    # Base
    "BaseModel",
    # GoverningBody
    "GoverningBody",
    "GoverningBodyCreate",
    "GoverningBodyUpdate",
    # Conference
    "Conference",
    "ConferenceCreate",
    "ConferenceUpdate",
    # PoliticalParty
    "PoliticalParty",
    "PoliticalPartyCreate",
    "PoliticalPartyUpdate",
    # Meeting
    "Meeting",
    "MeetingCreate",
    "MeetingUpdate",
    # Speaker
    "Speaker",
    "SpeakerCreate",
    "SpeakerUpdate",
    # Politician
    "Politician",
    "PoliticianCreate",
    "PoliticianUpdate",
    # ParliamentaryGroup
    "ParliamentaryGroup",
    "ParliamentaryGroupCreate",
    "ParliamentaryGroupUpdate",
    "ParliamentaryGroupMembership",
    "ParliamentaryGroupMembershipCreate",
]
