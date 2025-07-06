"""Use case for processing meeting minutes."""

from datetime import datetime

from src.application.dtos.minutes_dto import (
    ExtractedSpeechDTO,
    MinutesProcessingResultDTO,
    ProcessMinutesDTO,
)
from src.domain.entities.conversation import Conversation
from src.domain.entities.meeting import Meeting
from src.domain.entities.minutes import Minutes
from src.domain.repositories.conversation_repository import ConversationRepository
from src.domain.repositories.meeting_repository import MeetingRepository
from src.domain.repositories.minutes_repository import MinutesRepository
from src.domain.repositories.speaker_repository import SpeakerRepository
from src.domain.services.minutes_domain_service import MinutesDomainService
from src.domain.services.speaker_domain_service import SpeakerDomainService
from src.infrastructure.interfaces.pdf_processor_service import IPDFProcessorService
from src.infrastructure.interfaces.text_extractor_service import ITextExtractorService


class ProcessMinutesUseCase:
    """Use case for processing meeting minutes."""

    def __init__(
        self,
        meeting_repository: MeetingRepository,
        minutes_repository: MinutesRepository,
        conversation_repository: ConversationRepository,
        speaker_repository: SpeakerRepository,
        minutes_domain_service: MinutesDomainService,
        speaker_domain_service: SpeakerDomainService,
        pdf_processor: IPDFProcessorService,
        text_extractor: ITextExtractorService,
    ):
        self.meeting_repo = meeting_repository
        self.minutes_repo = minutes_repository
        self.conversation_repo = conversation_repository
        self.speaker_repo = speaker_repository
        self.minutes_service = minutes_domain_service
        self.speaker_service = speaker_domain_service
        self.pdf_processor = pdf_processor
        self.text_extractor = text_extractor

    async def execute(self, request: ProcessMinutesDTO) -> MinutesProcessingResultDTO:
        """Execute the minutes processing use case."""
        start_time = datetime.now()
        errors = []

        # Get meeting
        meeting = await self.meeting_repo.get_by_id(request.meeting_id)
        if not meeting:
            raise ValueError(f"Meeting {request.meeting_id} not found")

        # Check if minutes already exist
        if meeting.id is None:
            raise ValueError("Meeting must have an ID")
        existing_minutes = await self.minutes_repo.get_by_meeting(meeting.id)
        if existing_minutes and not request.force_reprocess:
            if self.minutes_service.is_minutes_processed(existing_minutes):
                raise ValueError(f"Minutes for meeting {meeting.id} already processed")

        # Create or get minutes record
        if not existing_minutes:
            if meeting.id is None:
                raise ValueError("Meeting must have an ID")
            minutes = Minutes(
                meeting_id=meeting.id,
                url=request.pdf_url or meeting.url,
            )
            minutes = await self.minutes_repo.create(minutes)
        else:
            minutes = existing_minutes

        try:
            # Extract speeches from minutes
            speeches = await self._extract_speeches(
                meeting, request.pdf_url, request.gcs_text_uri
            )

            # Create conversations from speeches
            if minutes.id is None:
                raise ValueError("Minutes must have an ID")
            conversations = self.minutes_service.create_conversations_from_speeches(
                speeches, minutes.id
            )

            # Save conversations
            saved_conversations = await self.conversation_repo.bulk_create(
                conversations
            )

            # Extract and create speakers
            unique_speakers = await self._extract_and_create_speakers(
                saved_conversations
            )

            # Mark minutes as processed
            if minutes.id is None:
                raise ValueError("Minutes must have an ID")
            await self.minutes_repo.mark_processed(minutes.id)

            # Calculate processing time
            end_time = datetime.now()
            processing_time = self.minutes_service.calculate_processing_duration(
                start_time, end_time
            )

            return MinutesProcessingResultDTO(
                minutes_id=minutes.id if minutes.id is not None else 0,
                meeting_id=meeting.id if meeting.id is not None else 0,
                total_conversations=len(saved_conversations),
                unique_speakers=unique_speakers,
                processing_time_seconds=processing_time,
                processed_at=end_time,
                errors=errors if errors else None,
            )

        except Exception as e:
            errors.append(str(e))
            raise

    async def _extract_speeches(
        self,
        meeting: Meeting,
        pdf_url: str | None,
        gcs_text_uri: str | None,
    ) -> list[ExtractedSpeechDTO]:
        """Extract speeches from minutes source."""
        if gcs_text_uri:
            # Extract from GCS text
            text_content = await self.text_extractor.extract_from_gcs(gcs_text_uri)
            speeches = await self.text_extractor.parse_speeches(text_content)
        elif pdf_url or meeting.gcs_pdf_uri:
            # Extract from PDF
            url = pdf_url or meeting.gcs_pdf_uri
            speeches = await self.pdf_processor.process_pdf(url)
        else:
            raise ValueError("No valid source for minutes processing")

        # Convert to DTOs
        return [
            ExtractedSpeechDTO(
                speaker_name=s.get("speaker", ""),
                content=s.get("content", ""),
                sequence_number=idx + 1,
            )
            for idx, s in enumerate(speeches)
        ]

    async def _extract_and_create_speakers(
        self, conversations: list[Conversation]
    ) -> int:
        """Extract unique speakers and create speaker records."""
        speaker_names = set()

        for conv in conversations:
            if conv.speaker_name:
                # Extract clean name and party info
                clean_name, party_info = self.speaker_service.extract_party_from_name(
                    conv.speaker_name
                )
                speaker_names.add((clean_name, party_info))

        # Create speaker records
        created_count = 0
        for name, party_info in speaker_names:
            # Check if speaker exists
            existing = await self.speaker_repo.get_by_name_party_position(
                name, party_info, None
            )

            if not existing:
                # Create new speaker
                from src.domain.entities.speaker import Speaker

                speaker = Speaker(
                    name=name,
                    political_party_name=party_info,
                    is_politician=bool(party_info),  # Assume politician if has party
                )
                await self.speaker_repo.create(speaker)
                created_count += 1

        return created_count
