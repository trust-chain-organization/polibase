"""Tests for PDF scraper"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.web_scraper.models import MinutesData
from src.web_scraper.pdf_scraper import PDFScraper
from src.web_scraper.scraper_service import ScraperService


class TestPDFScraper:
    """Test PDFScraper class"""

    @pytest.mark.asyncio
    async def test_fetch_minutes_success(self):
        """Test successfully fetching minutes from a PDF URL"""
        scraper = PDFScraper()

        # Mock the PDF handler
        mock_pdf_path = "/tmp/test.pdf"
        mock_text_content = "This is test content extracted from PDF."

        with patch.object(
            scraper.pdf_handler,
            "download_and_extract",
            new_callable=AsyncMock,
        ) as mock_download:
            mock_download.return_value = (mock_pdf_path, mock_text_content)

            # Execute
            result = await scraper.fetch_minutes("http://example.com/test.pdf")

            # Verify
            assert result is not None
            assert isinstance(result, MinutesData)
            assert result.content == mock_text_content
            assert result.pdf_url == "http://example.com/test.pdf"
            assert result.url == "http://example.com/test.pdf"
            assert result.metadata["source_type"] == "direct_pdf"
            assert result.metadata["pdf_path"] == mock_pdf_path
            assert len(result.speakers) == 0  # PDF scraper doesn't extract speakers

    @pytest.mark.asyncio
    async def test_fetch_minutes_download_failure(self):
        """Test handling PDF download failure"""
        scraper = PDFScraper()

        with patch.object(
            scraper.pdf_handler,
            "download_and_extract",
            new_callable=AsyncMock,
        ) as mock_download:
            mock_download.return_value = (None, "")

            # Execute
            result = await scraper.fetch_minutes("http://example.com/missing.pdf")

            # Verify
            assert result is None

    @pytest.mark.asyncio
    async def test_fetch_minutes_extraction_failure(self):
        """Test handling PDF text extraction failure"""
        scraper = PDFScraper()

        with patch.object(
            scraper.pdf_handler,
            "download_and_extract",
            new_callable=AsyncMock,
        ) as mock_download:
            mock_download.return_value = ("/tmp/test.pdf", "")

            # Execute
            result = await scraper.fetch_minutes("http://example.com/test.pdf")

            # Verify
            assert result is None

    def test_generate_ids_from_url(self):
        """Test generating council_id and schedule_id from URL"""
        scraper = PDFScraper()

        # Test with a sample URL
        council_id, schedule_id = scraper._generate_ids_from_url(
            "http://example.com/minutes/2024/test.pdf"
        )

        assert council_id.startswith("pdf_")
        assert len(council_id) == 12  # "pdf_" + 8 chars
        assert len(schedule_id) == 8

        # Same URL should generate same IDs
        council_id2, schedule_id2 = scraper._generate_ids_from_url(
            "http://example.com/minutes/2024/test.pdf"
        )
        assert council_id == council_id2
        assert schedule_id == schedule_id2

    def test_extract_title_from_url(self):
        """Test extracting title from PDF URL"""
        scraper = PDFScraper()

        # Test with filename
        title1 = scraper._extract_title_from_url(
            "http://example.com/meeting_minutes.pdf"
        )
        assert title1 == "meeting minutes"

        # Test with underscores and hyphens
        title2 = scraper._extract_title_from_url(
            "http://example.com/2024-01-15_council_meeting.pdf"
        )
        assert title2 == "2024 01 15 council meeting"

        # Test with no filename
        title3 = scraper._extract_title_from_url("http://example.com/")
        assert title3 == "Untitled PDF Document"

    @pytest.mark.asyncio
    async def test_extract_minutes_text_not_used(self):
        """Test that extract_minutes_text is not used for PDF scraper"""
        scraper = PDFScraper()
        result = await scraper.extract_minutes_text("<html>test</html>")
        assert result == ""

    @pytest.mark.asyncio
    async def test_extract_speakers_not_used(self):
        """Test that extract_speakers is not used for PDF scraper"""
        scraper = PDFScraper()
        result = await scraper.extract_speakers("<html>test</html>")
        assert result == []


class TestScraperServiceWithPDF:
    """Test ScraperService with PDF URLs"""

    @pytest.mark.asyncio
    async def test_scraper_service_recognizes_pdf_url(self):
        """Test that ScraperService recognizes PDF URLs and uses PDFScraper"""
        service = ScraperService(enable_gcs=False)

        # Mock the PDFScraper
        mock_minutes = MinutesData(
            council_id="test_council",
            schedule_id="test_schedule",
            title="Test Minutes",
            date=datetime.now(),
            content="Test content",
            speakers=[],
            url="http://example.com/test.pdf",
            scraped_at=datetime.now(),
            pdf_url="http://example.com/test.pdf",
        )

        with patch("src.web_scraper.pdf_scraper.PDFScraper") as mock_pdf_scraper_class:
            mock_scraper_instance = MagicMock()
            mock_scraper_instance.fetch_minutes = AsyncMock(return_value=mock_minutes)
            mock_pdf_scraper_class.return_value = mock_scraper_instance

            # Execute
            result = await service.fetch_from_url(
                "http://example.com/test.pdf", use_cache=False
            )

            # Verify
            assert result is not None
            assert result.pdf_url == "http://example.com/test.pdf"
            assert result.content == "Test content"
            mock_pdf_scraper_class.assert_called_once()

    @pytest.mark.asyncio
    async def test_scraper_service_pdf_case_insensitive(self):
        """Test that PDF URL matching is case-insensitive"""
        service = ScraperService(enable_gcs=False)

        # Test with uppercase .PDF extension
        scraper = service._get_scraper_for_url("http://example.com/test.PDF")
        assert scraper is not None
        assert scraper.__class__.__name__ == "PDFScraper"

        # Test with mixed case
        scraper = service._get_scraper_for_url("http://example.com/test.PdF")
        assert scraper is not None
        assert scraper.__class__.__name__ == "PDFScraper"

    def test_scraper_service_non_pdf_url(self):
        """Test that non-PDF URLs don't use PDFScraper"""
        service = ScraperService(enable_gcs=False)

        # Test with kaigiroku.net URL
        scraper = service._get_scraper_for_url(
            "https://kaigiroku.net/tenant/kyoto/SpMinuteView.html"
        )
        assert scraper is not None
        assert scraper.__class__.__name__ == "KaigirokuNetScraper"

        # Test with unsupported URL
        scraper = service._get_scraper_for_url("http://example.com/minutes.html")
        assert scraper is None


class TestPDFScraperIntegration:
    """Integration tests for PDF scraper (with mocked external dependencies)"""

    @pytest.mark.asyncio
    async def test_full_scraping_workflow_with_gcs_disabled(self):
        """Test full PDF scraping workflow without GCS upload"""
        service = ScraperService(enable_gcs=False)

        mock_minutes = MinutesData(
            council_id="pdf_12345678",
            schedule_id="87654321",
            title="test document",
            date=None,
            content="Extracted PDF content with multiple lines.",
            speakers=[],
            url="http://example.com/test_document.pdf",
            scraped_at=datetime.now(),
            pdf_url="http://example.com/test_document.pdf",
            metadata={"source_type": "direct_pdf", "pdf_path": "/tmp/test.pdf"},
        )

        with patch("src.web_scraper.pdf_scraper.PDFScraper") as mock_pdf_scraper_class:
            mock_scraper_instance = MagicMock()
            mock_scraper_instance.fetch_minutes = AsyncMock(return_value=mock_minutes)
            mock_pdf_scraper_class.return_value = mock_scraper_instance

            # Execute
            result = await service.fetch_from_url(
                "http://example.com/test_document.pdf", use_cache=False
            )

            # Verify
            assert result is not None
            assert result.content == "Extracted PDF content with multiple lines."
            assert result.pdf_url == "http://example.com/test_document.pdf"
            assert result.metadata["source_type"] == "direct_pdf"
            assert len(result.speakers) == 0

    @pytest.mark.asyncio
    async def test_export_to_text_without_gcs(self):
        """Test exporting PDF minutes to text file without GCS upload"""
        service = ScraperService(enable_gcs=False)

        minutes = MinutesData(
            council_id="test",
            schedule_id="123",
            title="Test PDF",
            date=datetime(2024, 1, 15),
            content="PDF content",
            speakers=[],
            url="http://example.com/test.pdf",
            scraped_at=datetime.now(),
            pdf_url="http://example.com/test.pdf",
        )

        # Mock file writing
        mock_file = MagicMock()
        with patch("builtins.open", return_value=mock_file) as mock_open:
            mock_file.__enter__.return_value = mock_file

            # Execute
            success, gcs_url = service.export_to_text(
                minutes, "/tmp/output.txt", upload_to_gcs=False
            )

            # Verify
            assert success is True
            assert gcs_url is None
            mock_open.assert_called_once()
            mock_file.write.assert_called_once()
