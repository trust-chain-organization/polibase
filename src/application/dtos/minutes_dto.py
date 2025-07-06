"""Minutes-related DTOs."""

from dataclasses import dataclass
from datetime import date, datetime


@dataclass
class ProcessMinutesDTO:
    """DTO for processing minutes request."""

    meeting_id: int
    pdf_url: str | None = None
    gcs_text_uri: str | None = None
    force_reprocess: bool = False


@dataclass
class MinutesProcessingResultDTO:
    """DTO for minutes processing result."""

    minutes_id: int
    meeting_id: int
    total_conversations: int
    unique_speakers: int
    processing_time_seconds: float
    processed_at: datetime
    errors: list[str] | None = None


@dataclass
class ExtractedSpeechDTO:
    """DTO for extracted speech from minutes."""

    speaker_name: str
    content: str
    sequence_number: int
    chapter_number: int | None = None


@dataclass
class MinutesDTO:
    """DTO for minutes data."""

    id: int
    meeting_id: int
    url: str | None
    processed_at: datetime | None
    meeting_date: date | None
    meeting_name: str | None
    conference_name: str | None
