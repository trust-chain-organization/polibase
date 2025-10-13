"""Minutes processing service implementation wrapping MinutesProcessAgent."""

import asyncio

from src.domain.services.interfaces.llm_service import ILLMService
from src.domain.services.interfaces.minutes_processing_service import (
    IMinutesProcessingService,
)
from src.minutes_divide_processor.minutes_process_agent import MinutesProcessAgent
from src.minutes_divide_processor.models import SpeakerAndSpeechContent


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
        # The agent's run method is synchronous, so we run it in an executor
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, self.agent.run, original_minutes)
        return result
