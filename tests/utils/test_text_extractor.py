"""Tests for text extraction utilities."""

from unittest.mock import MagicMock, patch

import pytest

from src.exceptions import PDFProcessingError, TextExtractionError
from src.utils.text_extractor import extract_text_from_file, extract_text_from_pdf


class TestExtractTextFromPdf:
    """Test cases for extract_text_from_pdf function."""

    def test_extract_text_from_pdf_empty_content(self):
        """Test error when PDF content is empty."""
        with pytest.raises(PDFProcessingError) as exc_info:
            extract_text_from_pdf(b"")

        assert "Empty PDF content provided" in str(exc_info.value)

    @patch("src.utils.text_extractor.pdfium.PdfDocument")
    def test_extract_text_from_pdf_no_pages(self, mock_pdf_class):
        """Test error when PDF has no pages."""
        # Setup
        mock_pdf = MagicMock()
        mock_pdf.__len__.return_value = 0
        mock_pdf_class.return_value = mock_pdf

        # Execute and verify
        with pytest.raises(PDFProcessingError) as exc_info:
            extract_text_from_pdf(b"dummy content")

        # Check that the error message contains the expected text
        # The actual error may be wrapped, so check the original message
        assert "PDF document has no pages" in str(exc_info.value)
        mock_pdf.close.assert_called_once()

    @patch("src.utils.text_extractor.pdfium.PdfDocument")
    def test_extract_text_from_pdf_success(self, mock_pdf_class):
        """Test successful text extraction from PDF."""
        # Setup
        mock_page1 = MagicMock()
        mock_page2 = MagicMock()

        mock_textpage1 = MagicMock()
        mock_textpage1.get_text_bounded.return_value = "Page 1 text"
        mock_page1.get_textpage.return_value = mock_textpage1

        mock_textpage2 = MagicMock()
        mock_textpage2.get_text_bounded.return_value = "Page 2 text"
        mock_page2.get_textpage.return_value = mock_textpage2

        mock_pdf = MagicMock()
        mock_pdf.__len__.return_value = 2
        mock_pdf.__iter__.return_value = [mock_page1, mock_page2]
        mock_pdf_class.return_value = mock_pdf

        # Execute
        result = extract_text_from_pdf(b"dummy content")

        # Verify
        assert result == "Page 1 text\nPage 2 text"
        mock_textpage1.close.assert_called_once()
        mock_textpage2.close.assert_called_once()
        mock_page1.close.assert_called_once()
        mock_page2.close.assert_called_once()
        mock_pdf.close.assert_called_once()

    @patch("src.utils.text_extractor.pdfium.PdfDocument")
    def test_extract_text_from_pdf_partial_failure(self, mock_pdf_class):
        """Test extraction when some pages fail."""
        # Setup
        mock_page1 = MagicMock()
        mock_page2 = MagicMock()

        # First page succeeds
        mock_textpage1 = MagicMock()
        mock_textpage1.get_text_bounded.return_value = "Page 1 text"
        mock_page1.get_textpage.return_value = mock_textpage1

        # Second page fails
        mock_page2.get_textpage.side_effect = Exception("Page error")

        mock_pdf = MagicMock()
        mock_pdf.__len__.return_value = 2
        mock_pdf.__iter__.return_value = [mock_page1, mock_page2]
        mock_pdf_class.return_value = mock_pdf

        # Execute
        result = extract_text_from_pdf(b"dummy content")

        # Verify - should still return text from successful page
        assert result == "Page 1 text"
        mock_textpage1.close.assert_called_once()
        mock_page1.close.assert_called_once()
        mock_page2.close.assert_called_once()

    @patch("src.utils.text_extractor.pdfium.PdfDocument")
    def test_extract_text_from_pdf_all_pages_fail(self, mock_pdf_class):
        """Test error when all pages fail to extract."""
        # Setup
        mock_page = MagicMock()
        mock_page.get_textpage.side_effect = Exception("Page error")

        mock_pdf = MagicMock()
        mock_pdf.__len__.return_value = 1
        mock_pdf.__iter__.return_value = [mock_page]
        mock_pdf_class.return_value = mock_pdf

        # Execute and verify
        with pytest.raises(TextExtractionError) as exc_info:
            extract_text_from_pdf(b"dummy content")

        assert "No text could be extracted from any page" in str(exc_info.value)
        mock_page.close.assert_called_once()

    @patch("src.utils.text_extractor.pdfium.PdfDocument")
    def test_extract_text_from_pdf_pdfium_error(self, mock_pdf_class):
        """Test handling of PdfiumError."""
        # Setup
        import pypdfium2 as pdfium

        mock_pdf_class.side_effect = pdfium.PdfiumError("Invalid PDF")

        # Execute and verify
        with pytest.raises(PDFProcessingError) as exc_info:
            extract_text_from_pdf(b"dummy content")

        assert "Failed to process PDF document" in str(exc_info.value)

    @patch("src.utils.text_extractor.pdfium.PdfDocument")
    def test_extract_text_from_pdf_unexpected_error(self, mock_pdf_class):
        """Test handling of unexpected errors."""
        # Setup
        mock_pdf_class.side_effect = RuntimeError("Unexpected error")

        # Execute and verify
        with pytest.raises(TextExtractionError) as exc_info:
            extract_text_from_pdf(b"dummy content")

        assert "Failed to extract text from PDF" in str(exc_info.value)


class TestExtractTextFromFile:
    """Test cases for extract_text_from_file function."""

    def test_extract_text_from_file_not_found(self):
        """Test error when file doesn't exist."""
        with pytest.raises(FileNotFoundError) as exc_info:
            extract_text_from_file("/nonexistent/file.pdf")

        assert "File not found" in str(exc_info.value)

    @patch("os.path.exists")
    @patch("builtins.open")
    @patch("src.utils.text_extractor.extract_text_from_pdf")
    def test_extract_text_from_file_pdf_success(
        self, mock_extract_pdf, mock_open, mock_exists
    ):
        """Test successful extraction from PDF file."""
        # Setup
        mock_exists.return_value = True
        mock_file = MagicMock()
        mock_file.read.return_value = b"PDF content"
        mock_open.return_value.__enter__.return_value = mock_file
        mock_extract_pdf.return_value = "Extracted text"

        # Execute
        result = extract_text_from_file("/path/to/file.pdf")

        # Verify
        assert result == "Extracted text"
        mock_open.assert_called_once_with("/path/to/file.pdf", "rb")
        mock_extract_pdf.assert_called_once_with(b"PDF content")

    @patch("os.path.exists")
    @patch("builtins.open", create=True)
    def test_extract_text_from_file_unsupported_format(self, mock_open, mock_exists):
        """Test error for unsupported file format."""
        # Setup
        mock_exists.return_value = True
        # Mock open to prevent actual file access
        mock_file = MagicMock()
        mock_file.read.return_value = b"some content"
        mock_open.return_value.__enter__.return_value = mock_file

        # Execute and verify
        with pytest.raises(TextExtractionError) as exc_info:
            extract_text_from_file("/path/to/file.txt")

        # The error might be wrapped, so check if it contains the expected message
        error_msg = str(exc_info.value)
        assert (
            "Unsupported file format" in error_msg
            or "Failed to extract text from file" in error_msg
        )

    @patch("os.path.exists")
    @patch("builtins.open")
    def test_extract_text_from_file_read_error(self, mock_open, mock_exists):
        """Test error when file reading fails."""
        # Setup
        mock_exists.return_value = True
        mock_open.side_effect = OSError("Read error")

        # Execute and verify
        with pytest.raises(TextExtractionError) as exc_info:
            extract_text_from_file("/path/to/file.pdf")

        assert "Failed to extract text from file" in str(exc_info.value)

    @patch("os.path.exists")
    @patch("builtins.open")
    @patch("src.utils.text_extractor.extract_text_from_pdf")
    def test_extract_text_from_file_pdf_error_propagation(
        self, mock_extract_pdf, mock_open, mock_exists
    ):
        """Test that PDF errors are properly propagated."""
        # Setup
        mock_exists.return_value = True
        mock_file = MagicMock()
        mock_file.read.return_value = b"PDF content"
        mock_open.return_value.__enter__.return_value = mock_file
        mock_extract_pdf.side_effect = PDFProcessingError("PDF error")

        # Execute and verify
        with pytest.raises(PDFProcessingError) as exc_info:
            extract_text_from_file("/path/to/file.pdf")

        assert "PDF error" in str(exc_info.value)
