"""Minutes processing service implementation wrapping MinutesProcessAgent."""

import asyncio

from src.domain.services.interfaces.llm_service import ILLMService
from src.domain.services.interfaces.minutes_processing_service import (
    IMinutesProcessingService,
)
from src.domain.value_objects.speaker_speech import SpeakerSpeech
from src.minutes_divide_processor.minutes_process_agent import MinutesProcessAgent


class MinutesProcessAgentService(IMinutesProcessingService):
    """Service that wraps MinutesProcessAgent for Clean Architecture compliance.

    This service implements the IMinutesProcessingService interface and delegates
    to the MinutesProcessAgent for the actual processing logic. This allows the
    application layer to depend on a domain interface rather than directly on
    infrastructure code.
    """

    def __init__(self, llm_service: ILLMService):
        """Initialize the minutes processing service.

        Args:
            llm_service: LLM service instance to use for processing
        """
        self.llm_service = llm_service
        self.agent = MinutesProcessAgent(llm_service=llm_service)

    async def process_minutes(self, original_minutes: str) -> list[SpeakerSpeech]:
        """Process meeting minutes text and extract speeches.

        This method wraps the synchronous MinutesProcessAgent and converts
        infrastructure-specific models to domain value objects.

        Args:
            original_minutes: Raw meeting minutes text content

        Returns:
            List of extracted speeches with speaker information as domain value objects

        Raises:
            ValueError: If processing fails or invalid input is provided
            TypeError: If the result format is invalid
        """
        # The agent's run method is synchronous, so we run it in an executor
        loop = asyncio.get_event_loop()
        infrastructure_results = await loop.run_in_executor(
            None, self.agent.run, original_minutes
        )

        # Convert infrastructure models to domain value objects
        domain_results = [
            SpeakerSpeech(
                speaker=result.speaker,
                speech_content=result.speech_content,
                chapter_number=result.chapter_number,
                sub_chapter_number=result.sub_chapter_number,
                speech_order=result.speech_order,
            )
            for result in infrastructure_results
        ]

        return domain_results
