"""Speaker DTOs for domain layer repository contracts."""

from dataclasses import dataclass


@dataclass
class SpeakerWithConversationCountDTO:
    """DTO for speaker with conversation count.

    This DTO is used in repository contracts and belongs to the domain layer.
    """

    id: int
    name: str
    type: str | None
    political_party_name: str | None
    position: str | None
    is_politician: bool
    conversation_count: int
