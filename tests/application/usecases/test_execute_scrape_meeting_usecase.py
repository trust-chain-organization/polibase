"""Tests for ExecuteScrapeMeetingUseCase."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.application.usecases.execute_scrape_meeting_usecase import (
    ExecuteScrapeMeetingDTO,
    ExecuteScrapeMeetingUseCase,
    ScrapeMeetingResultDTO,
)
from src.domain.entities.meeting import Meeting


class TestExecuteScrapeMeetingUseCase:
    """Test cases for ExecuteScrapeMeetingUseCase."""

    @pytest.fixture
    def mock_meeting_repository(self):
        """Create mock meeting repository."""
        repo = AsyncMock()
        return repo

    @pytest.fixture
    def use_case(self, mock_meeting_repository):
        """Create ExecuteScrapeMeetingUseCase instance."""
        return ExecuteScrapeMeetingUseCase(
            meeting_repository=mock_meeting_repository, enable_gcs=True
        )

    @pytest.fixture
    def sample_meeting(self):
        """Create a sample meeting entity."""
        from datetime import date

        return Meeting(
            id=1,
            url="https://example.com/meeting/123",
            name="サンプル会議",
            date=date(2024, 1, 1),
            conference_id=1,
        )

    @pytest.fixture
    def mock_scraper_service(self):
        """Create mock scraper service."""
        service = MagicMock()
        minutes = MagicMock()
        minutes.title = "会議録タイトル"
        minutes.speakers = ["Speaker1", "Speaker2"]
        minutes.content = "議事録の内容です。" * 100
        minutes.council_id = "council_123"
        minutes.schedule_id = "schedule_456"
        # Use AsyncMock for async method
        service.fetch_from_meeting_id = AsyncMock(return_value=minutes)
        service.export_to_text.return_value = (True, "gs://bucket/path/to/file.txt")
        return service

    @pytest.mark.asyncio
    async def test_execute_scrape_meeting_success(
        self,
        use_case,
        mock_meeting_repository,
        sample_meeting,
        mock_scraper_service,
    ):
        """Test successful meeting scraping with GCS upload."""
        # Arrange
        # Ensure sample_meeting has no GCS URI initially
        sample_meeting.gcs_text_uri = None
        sample_meeting.gcs_pdf_uri = None
        mock_meeting_repository.get_by_id.return_value = sample_meeting
        # Mock update will be called with the meeting after setting GCS URI
        mock_meeting_repository.update.return_value = sample_meeting

        request = ExecuteScrapeMeetingDTO(
            meeting_id=1, force_rescrape=False, upload_to_gcs=True
        )

        # Act
        with patch(
            "src.application.usecases.execute_scrape_meeting_usecase.ScraperService",
            return_value=mock_scraper_service,
        ):
            result = await use_case.execute(request)

        # Assert
        assert isinstance(result, ScrapeMeetingResultDTO)
        assert result.meeting_id == 1
        assert result.title == "会議録タイトル"
        assert result.speakers_count == 2
        assert result.gcs_text_uri == "gs://bucket/path/to/file.txt"
        assert result.errors is None or len(result.errors) == 0
        mock_meeting_repository.get_by_id.assert_called_once_with(1)
        mock_meeting_repository.update.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_meeting_not_found(self, use_case, mock_meeting_repository):
        """Test scraping when meeting does not exist."""
        # Arrange
        mock_meeting_repository.get_by_id.return_value = None

        request = ExecuteScrapeMeetingDTO(meeting_id=999)

        # Act & Assert
        with pytest.raises(ValueError, match="Meeting 999 not found"):
            await use_case.execute(request)

        mock_meeting_repository.get_by_id.assert_called_once_with(999)

    @pytest.mark.asyncio
    async def test_execute_meeting_no_url(
        self, use_case, mock_meeting_repository, sample_meeting
    ):
        """Test scraping when meeting has no URL set."""
        # Arrange
        from datetime import date

        meeting_no_url = Meeting(
            id=1, name="サンプル会議", date=date(2024, 1, 1), conference_id=1
        )
        mock_meeting_repository.get_by_id.return_value = meeting_no_url

        request = ExecuteScrapeMeetingDTO(meeting_id=1)

        # Act & Assert
        with pytest.raises(ValueError, match="does not have a URL set"):
            await use_case.execute(request)

    @pytest.mark.asyncio
    async def test_execute_already_scraped_no_force(
        self, use_case, mock_meeting_repository
    ):
        """Test scraping when meeting already has GCS URI without force rescrape."""
        # Arrange
        from datetime import date

        meeting_with_gcs = Meeting(
            id=1,
            url="https://example.com/meeting/123",
            name="サンプル会議",
            date=date(2024, 1, 1),
            conference_id=1,
            gcs_text_uri="gs://bucket/existing.txt",
        )
        mock_meeting_repository.get_by_id.return_value = meeting_with_gcs

        request = ExecuteScrapeMeetingDTO(meeting_id=1, force_rescrape=False)

        # Act & Assert
        with pytest.raises(ValueError, match="already has scraped data"):
            await use_case.execute(request)

    @pytest.mark.asyncio
    async def test_execute_force_rescrape(
        self,
        use_case,
        mock_meeting_repository,
        mock_scraper_service,
    ):
        """Test force re-scraping existing meeting data."""
        # Arrange
        from datetime import date

        meeting_with_old_gcs = Meeting(
            id=1,
            url="https://example.com/meeting/123",
            name="サンプル会議",
            date=date(2024, 1, 1),
            conference_id=1,
            gcs_text_uri="gs://bucket/old.txt",
        )
        mock_meeting_repository.get_by_id.return_value = meeting_with_old_gcs
        mock_meeting_repository.update.return_value = meeting_with_old_gcs

        request = ExecuteScrapeMeetingDTO(meeting_id=1, force_rescrape=True)

        # Act
        with patch(
            "src.application.usecases.execute_scrape_meeting_usecase.ScraperService",
            return_value=mock_scraper_service,
        ):
            result = await use_case.execute(request)

        # Assert
        assert result.meeting_id == 1
        assert result.gcs_text_uri == "gs://bucket/path/to/file.txt"
        mock_meeting_repository.update.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_scraping_failed(
        self, use_case, mock_meeting_repository, sample_meeting
    ):
        """Test when scraping fails to extract minutes."""
        # Arrange
        sample_meeting.gcs_text_uri = None
        sample_meeting.gcs_pdf_uri = None
        mock_meeting_repository.get_by_id.return_value = sample_meeting

        mock_scraper = MagicMock()
        mock_scraper.fetch_from_meeting_id = AsyncMock(return_value=None)

        request = ExecuteScrapeMeetingDTO(meeting_id=1)

        # Act & Assert
        with patch(
            "src.application.usecases.execute_scrape_meeting_usecase.ScraperService",
            return_value=mock_scraper,
        ):
            with pytest.raises(ValueError, match="Failed to scrape minutes"):
                await use_case.execute(request)

    @pytest.mark.asyncio
    async def test_execute_without_gcs_upload(
        self,
        use_case,
        mock_meeting_repository,
        sample_meeting,
    ):
        """Test scraping without GCS upload."""
        # Arrange
        sample_meeting.gcs_text_uri = None
        sample_meeting.gcs_pdf_uri = None
        mock_meeting_repository.get_by_id.return_value = sample_meeting

        mock_scraper = MagicMock()
        minutes = MagicMock()
        minutes.title = "会議録"
        minutes.speakers = ["Speaker1"]
        minutes.content = "内容"
        minutes.council_id = "council_123"
        minutes.schedule_id = "schedule_456"
        mock_scraper.fetch_from_meeting_id = AsyncMock(return_value=minutes)
        mock_scraper.export_to_text.return_value = (True, None)

        request = ExecuteScrapeMeetingDTO(meeting_id=1, upload_to_gcs=False)

        # Act
        with patch(
            "src.application.usecases.execute_scrape_meeting_usecase.ScraperService",
            return_value=mock_scraper,
        ):
            result = await use_case.execute(request)

        # Assert
        assert result.meeting_id == 1
        assert result.gcs_text_uri is None
        assert result.gcs_pdf_uri is None

    @pytest.mark.asyncio
    async def test_execute_text_export_failed(
        self,
        use_case,
        mock_meeting_repository,
        sample_meeting,
    ):
        """Test when text file export fails."""
        # Arrange
        sample_meeting.gcs_text_uri = None
        sample_meeting.gcs_pdf_uri = None
        mock_meeting_repository.get_by_id.return_value = sample_meeting

        mock_scraper = MagicMock()
        minutes = MagicMock()
        minutes.title = "会議録"
        minutes.speakers = ["Speaker1"]
        minutes.content = "内容"
        minutes.council_id = "council_123"
        minutes.schedule_id = "schedule_456"
        mock_scraper.fetch_from_meeting_id = AsyncMock(return_value=minutes)
        mock_scraper.export_to_text.return_value = (False, None)

        request = ExecuteScrapeMeetingDTO(meeting_id=1, upload_to_gcs=False)

        # Act
        with patch(
            "src.application.usecases.execute_scrape_meeting_usecase.ScraperService",
            return_value=mock_scraper,
        ):
            result = await use_case.execute(request)

        # Assert
        assert result.errors is not None
        assert "Failed to save scraped minutes" in result.errors[0]

    @pytest.mark.asyncio
    async def test_execute_meeting_update_failed(
        self,
        use_case,
        mock_meeting_repository,
        sample_meeting,
        mock_scraper_service,
    ):
        """Test when meeting update fails after scraping."""
        # Arrange
        sample_meeting.gcs_text_uri = None
        sample_meeting.gcs_pdf_uri = None
        mock_meeting_repository.get_by_id.return_value = sample_meeting
        mock_meeting_repository.update.return_value = None

        request = ExecuteScrapeMeetingDTO(meeting_id=1, upload_to_gcs=True)

        # Act
        with patch(
            "src.application.usecases.execute_scrape_meeting_usecase.ScraperService",
            return_value=mock_scraper_service,
        ):
            result = await use_case.execute(request)

        # Assert
        assert result.errors is not None
        assert "Failed to update meeting with GCS URIs" in result.errors

    @pytest.mark.asyncio
    async def test_execute_processing_time_recorded(
        self,
        use_case,
        mock_meeting_repository,
        sample_meeting,
        mock_scraper_service,
    ):
        """Test that processing time is properly recorded."""
        # Arrange
        sample_meeting.gcs_text_uri = None
        sample_meeting.gcs_pdf_uri = None
        mock_meeting_repository.get_by_id.return_value = sample_meeting
        mock_meeting_repository.update.return_value = sample_meeting

        request = ExecuteScrapeMeetingDTO(meeting_id=1)

        # Act
        with patch(
            "src.application.usecases.execute_scrape_meeting_usecase.ScraperService",
            return_value=mock_scraper_service,
        ):
            result = await use_case.execute(request)

        # Assert
        assert result.processing_time_seconds >= 0
        assert isinstance(result.processed_at, datetime)
