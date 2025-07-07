"""Unit tests for web scraper exceptions"""

import pytest

from src.web_scraper.exceptions import (
    CacheError,
    GCSUploadError,
    PDFDownloadError,
    PDFExtractionError,
    ScraperConnectionError,
    ScraperError,
    ScraperParseError,
    ScraperTimeoutError,
)


class TestScraperExceptions:
    """Test cases for scraper exceptions"""

    def test_base_scraper_error(self):
        """Test base ScraperError"""
        error = ScraperError("Base error message")
        assert str(error) == "Base error message"
        assert isinstance(error, Exception)

    def test_scraper_connection_error(self):
        """Test ScraperConnectionError"""
        error = ScraperConnectionError("Failed to connect to website")
        assert str(error) == "Failed to connect to website"
        assert isinstance(error, ScraperError)

    def test_scraper_parse_error(self):
        """Test ScraperParseError"""
        error = ScraperParseError("Failed to parse HTML content")
        assert str(error) == "Failed to parse HTML content"
        assert isinstance(error, ScraperError)

    def test_scraper_timeout_error(self):
        """Test ScraperTimeoutError"""
        error = ScraperTimeoutError("Request timed out after 30 seconds")
        assert str(error) == "Request timed out after 30 seconds"
        assert isinstance(error, ScraperError)

    def test_pdf_download_error(self):
        """Test PDFDownloadError"""
        error = PDFDownloadError("Failed to download PDF from URL")
        assert str(error) == "Failed to download PDF from URL"
        assert isinstance(error, ScraperError)

    def test_pdf_extraction_error(self):
        """Test PDFExtractionError"""
        error = PDFExtractionError("Failed to extract text from PDF")
        assert str(error) == "Failed to extract text from PDF"
        assert isinstance(error, ScraperError)

    def test_cache_error(self):
        """Test CacheError"""
        error = CacheError("Failed to read from cache")
        assert str(error) == "Failed to read from cache"
        assert isinstance(error, ScraperError)

    def test_gcs_upload_error(self):
        """Test GCSUploadError"""
        error = GCSUploadError("Failed to upload to Google Cloud Storage")
        assert str(error) == "Failed to upload to Google Cloud Storage"
        assert isinstance(error, ScraperError)

    def test_exception_inheritance(self):
        """Test exception inheritance chain"""
        # Create instances
        base_error = ScraperError("base")
        connection_error = ScraperConnectionError("connection")

        # Test inheritance
        assert isinstance(base_error, Exception)
        assert isinstance(connection_error, Exception)
        assert isinstance(connection_error, ScraperError)

        # Test that subclasses are not instances of each other
        parse_error = ScraperParseError("parse")
        timeout_error = ScraperTimeoutError("timeout")

        assert not isinstance(parse_error, ScraperTimeoutError)
        assert not isinstance(timeout_error, ScraperParseError)

    def test_exception_raising(self):
        """Test raising and catching exceptions"""
        # Test raising and catching specific exception
        with pytest.raises(ScraperConnectionError) as exc_info:
            raise ScraperConnectionError("Connection failed")

        assert "Connection failed" in str(exc_info.value)

        # Test catching base exception catches subclass
        try:
            raise PDFDownloadError("PDF error")
        except ScraperError as e:
            assert isinstance(e, PDFDownloadError)
            assert str(e) == "PDF error"

    def test_exception_with_additional_context(self):
        """Test exceptions can carry additional context"""
        # Create exception with additional attributes
        error = ScraperConnectionError("Failed to connect")
        error.url = "http://example.com"
        error.status_code = 404

        # Verify attributes
        assert error.url == "http://example.com"
        assert error.status_code == 404
        assert str(error) == "Failed to connect"
