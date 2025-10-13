"""Minutes processing service interface definition for domain layer."""

from typing import Protocol

from src.minutes_divide_processor.models import SpeakerAndSpeechContent


class IMinutesProcessingService(Protocol):
    """Interface for minutes processing services.

    This is a Protocol (interface) that defines the contract for minutes
    processing services. It belongs to the domain layer as it represents a
    core business capability for extracting speeches from meeting minutes text.
    """

    async def process_minutes(
        self, original_minutes: str
    ) -> list[SpeakerAndSpeechContent]:
        """Process meeting minutes text and extract speeches.

        Args:
            original_minutes: Raw meeting minutes text content

        Returns:
            List of extracted speeches with speaker information

        Raises:
            ValueError: If processing fails or invalid input is provided
            TypeError: If the result format is invalid
        """
        ...
