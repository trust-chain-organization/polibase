"""Meeting repository interface."""

from abc import abstractmethod
from datetime import date

from src.domain.entities.meeting import Meeting
from src.domain.repositories.base import BaseRepository


class MeetingRepository(BaseRepository[Meeting]):
    """Repository interface for meetings."""

    @abstractmethod
    async def get_by_conference_and_date(
        self, conference_id: int, meeting_date: date
    ) -> Meeting | None:
        """Get meeting by conference and date."""
        pass

    @abstractmethod
    async def get_by_conference(
        self, conference_id: int, limit: int | None = None
    ) -> list[Meeting]:
        """Get all meetings for a conference."""
        pass

    @abstractmethod
    async def get_unprocessed(self, limit: int | None = None) -> list[Meeting]:
        """Get meetings that haven't been processed yet."""
        pass

    @abstractmethod
    async def update_gcs_uris(
        self,
        meeting_id: int,
        pdf_uri: str | None = None,
        text_uri: str | None = None,
    ) -> bool:
        """Update GCS URIs for a meeting."""
        pass
