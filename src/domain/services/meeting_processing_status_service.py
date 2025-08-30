"""Meeting processing status service."""

from typing import TypedDict

from src.domain.repositories.conversation_repository import ConversationRepository
from src.domain.repositories.minutes_repository import MinutesRepository
from src.domain.repositories.speaker_repository import SpeakerRepository


class ProcessingStatus(TypedDict):
    """Processing status of a meeting."""

    has_minutes: bool
    has_conversations: bool
    has_speakers: bool
    conversation_count: int
    speaker_count: int


class MeetingProcessingStatusService:
    """Service for checking meeting processing status."""

    def __init__(
        self,
        minutes_repository: MinutesRepository,
        conversation_repository: ConversationRepository,
        speaker_repository: SpeakerRepository,
    ) -> None:
        """Initialize the service with repositories."""
        self.minutes_repository = minutes_repository
        self.conversation_repository = conversation_repository
        self.speaker_repository = speaker_repository
        self._cache: dict[int, ProcessingStatus] = {}

    async def has_conversations(self, meeting_id: int) -> bool:
        """Check if a meeting has any conversations extracted.

        Args:
            meeting_id: The ID of the meeting to check

        Returns:
            True if the meeting has conversations, False otherwise
        """
        # Check cache first
        if meeting_id in self._cache:
            return self._cache[meeting_id]["has_conversations"]

        # Get minutes for the meeting
        minutes = await self.minutes_repository.get_by_meeting(meeting_id)
        if not minutes:
            return False

        # Check if minutes has conversations
        if minutes.id is None:
            return False
        conversations = await self.conversation_repository.get_by_minutes(minutes.id)
        return len(conversations) > 0

    async def has_speakers(self, meeting_id: int) -> bool:
        """Check if a meeting has any speakers extracted.

        Args:
            meeting_id: The ID of the meeting to check

        Returns:
            True if the meeting has speakers, False otherwise
        """
        # Check cache first
        if meeting_id in self._cache:
            return self._cache[meeting_id]["has_speakers"]

        # Get minutes for the meeting
        minutes = await self.minutes_repository.get_by_meeting(meeting_id)
        if not minutes:
            return False

        # Check if minutes has conversations with speakers
        if minutes.id is None:
            return False
        conversations = await self.conversation_repository.get_by_minutes(minutes.id)
        # Check if any conversation has a speaker_id
        for conversation in conversations:
            if conversation.speaker_id is not None:
                return True

        return False

    async def get_processing_status(self, meeting_id: int) -> ProcessingStatus:
        """Get comprehensive processing status for a meeting.

        Args:
            meeting_id: The ID of the meeting to check

        Returns:
            ProcessingStatus dictionary with status information
        """
        # Check cache first
        if meeting_id in self._cache:
            return self._cache[meeting_id]

        # Initialize status
        status: ProcessingStatus = {
            "has_minutes": False,
            "has_conversations": False,
            "has_speakers": False,
            "conversation_count": 0,
            "speaker_count": 0,
        }

        # Get minutes for the meeting
        minutes = await self.minutes_repository.get_by_meeting(meeting_id)
        if not minutes:
            self._cache[meeting_id] = status
            return status

        status["has_minutes"] = True

        # Collect all conversations and speaker IDs
        if minutes.id is None:
            self._cache[meeting_id] = status
            return status
        conversations = await self.conversation_repository.get_by_minutes(minutes.id)
        speaker_ids: set[int] = set()

        # Collect unique speaker IDs
        for conversation in conversations:
            if conversation.speaker_id is not None:
                speaker_ids.add(conversation.speaker_id)

        # Update status
        if conversations:
            status["has_conversations"] = True
            status["conversation_count"] = len(conversations)

        if speaker_ids:
            status["has_speakers"] = True
            status["speaker_count"] = len(speaker_ids)

        # Cache the result
        self._cache[meeting_id] = status

        return status

    def clear_cache(self, meeting_id: int | None = None) -> None:
        """Clear cached status.

        Args:
            meeting_id: The meeting ID to clear from cache.
                       If None, clears entire cache.
        """
        if meeting_id is None:
            self._cache.clear()
        else:
            self._cache.pop(meeting_id, None)
