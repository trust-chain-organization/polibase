"""Comprehensive tests for KaigirokuNetScraper

Following Phase 1 (KokkaiScraper) success pattern with category-based testing.
Focuses on high-coverage methods to reach >80% target from current 31.1%.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.web_scraper.kaigiroku_net_scraper import KaigirokuNetScraper
from src.web_scraper.models import MinutesData


class TestKaigirokuNetScraperInitialization:
    """Test scraper initialization"""

    def test_init_with_defaults(self):
        """Test scraper initializes with default parameters"""
        scraper = KaigirokuNetScraper()

        assert scraper.headless is True
        assert scraper.content_extractor is not None
        assert scraper.speaker_extractor is not None
        assert scraper.pdf_handler is not None
        assert scraper.file_handler is not None

    def test_init_with_custom_params(self):
        """Test scraper initializes with custom parameters"""
        scraper = KaigirokuNetScraper(headless=False, download_dir="custom/path")

        assert scraper.headless is False
        # PDF handler should use custom download_dir
        assert hasattr(scraper.pdf_handler, "download_dir")


class TestKaigirokuNetScraperURLParsing:
    """Test URL parameter extraction"""

    def test_extract_url_params_valid_url(self):
        """Test extracting council_id and schedule_id from valid URL"""
        scraper = KaigirokuNetScraper()
        url = "https://ssp.kaigiroku.net/tenant/kyoto/MinuteView.html?council_id=6030&schedule_id=1"

        council_id, schedule_id = scraper._extract_url_params(url)

        assert council_id == "6030"
        assert schedule_id == "1"

    def test_extract_url_params_different_tenant(self):
        """Test extracting params from different tenant URL"""
        scraper = KaigirokuNetScraper()
        url = "https://ssp.kaigiroku.net/tenant/osaka/MinuteView.html?council_id=1234&schedule_id=99"

        council_id, schedule_id = scraper._extract_url_params(url)

        assert council_id == "1234"
        assert schedule_id == "99"

    def test_extract_url_params_missing_parameters(self):
        """Test extracting params from URL without required parameters"""
        scraper = KaigirokuNetScraper()
        url = "https://ssp.kaigiroku.net/tenant/kyoto/MinuteView.html"

        council_id, schedule_id = scraper._extract_url_params(url)

        # Should return None for missing parameters
        assert council_id is None or council_id == ""
        assert schedule_id is None or schedule_id == ""


class TestKaigirokuNetScraperDateExtraction:
    """Test date extraction from page content"""

    @pytest.mark.asyncio
    async def test_extract_date_reiwa_format(self):
        """Test extracting date in Reiwa format"""
        scraper = KaigirokuNetScraper()
        mock_page = AsyncMock()
        mock_page.query_selector = AsyncMock(return_value=MagicMock())
        mock_page.evaluate = AsyncMock(return_value="令和7年1月23日")

        date_str = await scraper._extract_date(mock_page)

        assert date_str == "2025-01-23"

    @pytest.mark.asyncio
    async def test_extract_date_heisei_format(self):
        """Test extracting date in Heisei format"""
        scraper = KaigirokuNetScraper()
        mock_page = AsyncMock()
        mock_page.query_selector = AsyncMock(return_value=MagicMock())
        mock_page.evaluate = AsyncMock(return_value="平成16年9月22日")

        date_str = await scraper._extract_date(mock_page)

        assert date_str == "2004-09-22"

    @pytest.mark.asyncio
    async def test_extract_date_western_format(self):
        """Test extracting date in Western calendar format"""
        scraper = KaigirokuNetScraper()
        mock_page = AsyncMock()
        mock_page.query_selector = AsyncMock(return_value=MagicMock())
        mock_page.evaluate = AsyncMock(return_value="2024年12月31日")

        date_str = await scraper._extract_date(mock_page)

        assert date_str == "2024-12-31"

    @pytest.mark.asyncio
    async def test_extract_date_no_element(self):
        """Test date extraction when date element not found"""
        scraper = KaigirokuNetScraper()
        mock_page = AsyncMock()
        mock_page.query_selector = AsyncMock(return_value=None)

        date_str = await scraper._extract_date(mock_page)

        assert date_str is None

    @pytest.mark.asyncio
    async def test_extract_date_invalid_format(self):
        """Test date extraction with invalid date format"""
        scraper = KaigirokuNetScraper()
        mock_page = AsyncMock()
        mock_page.query_selector = AsyncMock(return_value=MagicMock())
        mock_page.evaluate = AsyncMock(return_value="Invalid Date")

        date_str = await scraper._extract_date(mock_page)

        # Should handle gracefully (return None or empty string)
        assert date_str is None or date_str == ""


class TestKaigirokuNetScraperPDFURLFinding:
    """Test PDF download URL finding"""

    @pytest.mark.asyncio
    async def test_find_pdf_download_url_found_in_buttons(self):
        """Test finding PDF URL in download buttons"""
        scraper = KaigirokuNetScraper()
        mock_page = AsyncMock()

        # Mock button with PDF link
        mock_button = AsyncMock()
        mock_button.get_attribute = AsyncMock(
            return_value="https://example.com/minutes.pdf"
        )
        mock_page.query_selector = AsyncMock(return_value=mock_button)

        pdf_url = await scraper._find_pdf_download_url(mock_page)

        assert pdf_url == "https://example.com/minutes.pdf"

    @pytest.mark.asyncio
    async def test_find_pdf_download_url_not_found(self):
        """Test PDF URL not found"""
        scraper = KaigirokuNetScraper()
        mock_page = AsyncMock()
        mock_page.query_selector = AsyncMock(return_value=None)
        mock_page.query_selector_all = AsyncMock(return_value=[])

        pdf_url = await scraper._find_pdf_download_url(mock_page)

        assert pdf_url is None

    @pytest.mark.asyncio
    async def test_find_pdf_download_url_found_in_links(self):
        """Test finding PDF URL in anchor tags"""
        scraper = KaigirokuNetScraper()
        mock_page = AsyncMock()

        # No button, but anchor tag with PDF
        mock_page.query_selector = AsyncMock(return_value=None)
        mock_link = AsyncMock()
        mock_link.get_attribute = AsyncMock(
            return_value="https://example.com/document.pdf"
        )
        mock_page.query_selector_all = AsyncMock(return_value=[mock_link])

        pdf_url = await scraper._find_pdf_download_url(mock_page)

        assert pdf_url == "https://example.com/document.pdf"


class TestKaigirokuNetScraperTextViewURLFinding:
    """Test text view URL finding"""

    @pytest.mark.asyncio
    async def test_find_text_view_url_found(self):
        """Test finding text view URL"""
        scraper = KaigirokuNetScraper()
        mock_page = AsyncMock()

        mock_link = AsyncMock()
        mock_link.get_attribute = AsyncMock(
            return_value="TextView.html?council_id=6030&schedule_id=1"
        )
        mock_page.query_selector = AsyncMock(return_value=mock_link)

        text_url = await scraper._find_text_view_url(mock_page)

        assert text_url is not None
        assert "TextView.html" in text_url

    @pytest.mark.asyncio
    async def test_find_text_view_url_not_found(self):
        """Test text view URL not found"""
        scraper = KaigirokuNetScraper()
        mock_page = AsyncMock()
        mock_page.query_selector = AsyncMock(return_value=None)
        mock_page.query_selector_all = AsyncMock(return_value=[])

        text_url = await scraper._find_text_view_url(mock_page)

        assert text_url is None


class TestKaigirokuNetScraperIframeExtraction:
    """Test iframe content extraction"""

    @pytest.mark.asyncio
    async def test_extract_iframe_content_found(self):
        """Test extracting content from iframe"""
        scraper = KaigirokuNetScraper()
        mock_page = AsyncMock()

        # Mock iframe
        mock_iframe_elem = AsyncMock()
        mock_iframe = AsyncMock()
        mock_iframe.content = AsyncMock(
            return_value="<html><body>Iframe content</body></html>"
        )
        mock_iframe_elem.content_frame = AsyncMock(return_value=mock_iframe)

        mock_page.query_selector = AsyncMock(return_value=mock_iframe_elem)

        iframe_content = await scraper._extract_iframe_content(mock_page)

        assert iframe_content == "<html><body>Iframe content</body></html>"

    @pytest.mark.asyncio
    async def test_extract_iframe_content_not_found(self):
        """Test iframe not found"""
        scraper = KaigirokuNetScraper()
        mock_page = AsyncMock()
        mock_page.query_selector = AsyncMock(return_value=None)
        mock_page.query_selector_all = AsyncMock(return_value=[])

        iframe_content = await scraper._extract_iframe_content(mock_page)

        assert iframe_content is None

    @pytest.mark.asyncio
    async def test_extract_iframe_content_error(self):
        """Test iframe extraction with error"""
        scraper = KaigirokuNetScraper()
        mock_page = AsyncMock()

        mock_iframe_elem = AsyncMock()
        mock_iframe_elem.content_frame = AsyncMock(side_effect=Exception("Frame error"))
        mock_page.query_selector = AsyncMock(return_value=mock_iframe_elem)

        iframe_content = await scraper._extract_iframe_content(mock_page)

        assert iframe_content is None


class TestKaigirokuNetScraperWaitForContent:
    """Test content waiting logic"""

    @pytest.mark.asyncio
    async def test_wait_for_content_success_first_try(self):
        """Test waiting succeeds on first try"""
        scraper = KaigirokuNetScraper()
        mock_page = AsyncMock()
        mock_page.query_selector = AsyncMock(return_value=MagicMock())  # Element found

        # Should not raise, completes successfully
        await scraper._wait_for_content(mock_page)

        mock_page.query_selector.assert_called()

    @pytest.mark.asyncio
    async def test_wait_for_content_timeout_then_success(self):
        """Test waiting with initial timeout then success"""
        scraper = KaigirokuNetScraper()
        mock_page = AsyncMock()

        # First call times out, second succeeds
        mock_page.query_selector = AsyncMock(side_effect=[None, MagicMock()])
        mock_page.wait_for_timeout = AsyncMock()

        await scraper._wait_for_content(mock_page)

        # Should have retried
        assert mock_page.query_selector.call_count >= 1


class TestKaigirokuNetScraperPDFDownload:
    """Test PDF download and minutes creation"""

    @pytest.mark.asyncio
    async def test_download_pdf_as_minutes_success(self):
        """Test successful PDF download and conversion to MinutesData"""
        scraper = KaigirokuNetScraper()

        # Mock PDF handler
        with patch.object(
            scraper.pdf_handler,
            "download_pdf",
            return_value="/path/to/downloaded.pdf",
        ):
            with patch.object(
                scraper.pdf_handler,
                "convert_pdf_to_text",
                return_value="PDF content text",
            ):
                result = await scraper._download_pdf_as_minutes(
                    "https://example.com/minutes.pdf",
                    "https://source.url",
                    "123",
                    "456",
                )

                assert result is not None
                assert isinstance(result, MinutesData)
                assert result.council_id == "123"
                assert result.schedule_id == "456"
                assert "PDF content text" in result.content

    @pytest.mark.asyncio
    async def test_download_pdf_as_minutes_download_failure(self):
        """Test PDF download failure"""
        scraper = KaigirokuNetScraper()

        # Mock PDF download failure
        with patch.object(
            scraper.pdf_handler,
            "download_pdf",
            return_value=None,
        ):
            result = await scraper._download_pdf_as_minutes(
                "https://example.com/minutes.pdf",
                "https://source.url",
                "123",
                "456",
            )

            assert result is None


class TestKaigirokuNetScraperMainFlow:
    """Test main fetch_minutes flow with various scenarios"""

    @pytest.mark.asyncio
    async def test_fetch_minutes_with_pdf_flow(self):
        """Test fetch_minutes when PDF is available"""
        scraper = KaigirokuNetScraper()
        test_url = "https://ssp.kaigiroku.net/tenant/kyoto/MinuteView.html?council_id=100&schedule_id=1"

        mock_page = AsyncMock()
        mock_page.goto = AsyncMock(return_value=AsyncMock(status=200))
        mock_page.wait_for_load_state = AsyncMock()

        mock_context = AsyncMock()
        mock_context.new_page = AsyncMock(return_value=mock_page)

        mock_browser = AsyncMock()
        mock_browser.new_context = AsyncMock(return_value=mock_context)
        mock_browser.close = AsyncMock()

        with patch("src.web_scraper.kaigiroku_net_scraper.async_playwright") as mock_pw:
            mock_p = AsyncMock()
            mock_p.chromium.launch = AsyncMock(return_value=mock_browser)
            mock_pw.return_value.__aenter__.return_value = mock_p

            # Mock to return PDF URL
            with patch.object(
                scraper,
                "_find_pdf_download_url",
                AsyncMock(return_value="https://example.com/minutes.pdf"),
            ):
                with patch.object(
                    scraper,
                    "_download_pdf_as_minutes",
                    AsyncMock(
                        return_value=MinutesData(
                            url=test_url,
                            title="Test Minutes",
                            content="Test content from PDF",
                            council_id="100",
                            schedule_id="1",
                        )
                    ),
                ):
                    result = await scraper.fetch_minutes(test_url)

                    assert result is not None
                    assert result.council_id == "100"
                    assert "PDF" in result.content

    @pytest.mark.asyncio
    async def test_fetch_minutes_no_response(self):
        """Test fetch_minutes when server returns no response"""
        scraper = KaigirokuNetScraper()
        test_url = "https://ssp.kaigiroku.net/tenant/test/MinuteView.html?council_id=1&schedule_id=1"

        mock_page = AsyncMock()
        mock_page.goto = AsyncMock(return_value=None)  # No response

        mock_context = AsyncMock()
        mock_context.new_page = AsyncMock(return_value=mock_page)

        mock_browser = AsyncMock()
        mock_browser.new_context = AsyncMock(return_value=mock_context)
        mock_browser.close = AsyncMock()

        with patch("src.web_scraper.kaigiroku_net_scraper.async_playwright") as mock_pw:
            mock_p = AsyncMock()
            mock_p.chromium.launch = AsyncMock(return_value=mock_browser)
            mock_pw.return_value.__aenter__.return_value = mock_p

            result = await scraper.fetch_minutes(test_url)

            assert result is None

    @pytest.mark.asyncio
    async def test_fetch_minutes_exception_handling(self):
        """Test fetch_minutes handles exceptions gracefully"""
        scraper = KaigirokuNetScraper()
        test_url = "https://ssp.kaigiroku.net/tenant/test/MinuteView.html?council_id=1&schedule_id=1"

        mock_page = AsyncMock()
        mock_page.goto = AsyncMock(side_effect=Exception("Network error"))

        mock_context = AsyncMock()
        mock_context.new_page = AsyncMock(return_value=mock_page)

        mock_browser = AsyncMock()
        mock_browser.new_context = AsyncMock(return_value=mock_context)
        mock_browser.close = AsyncMock()

        with patch("src.web_scraper.kaigiroku_net_scraper.async_playwright") as mock_pw:
            mock_p = AsyncMock()
            mock_p.chromium.launch = AsyncMock(return_value=mock_browser)
            mock_pw.return_value.__aenter__.return_value = mock_p

            result = await scraper.fetch_minutes(test_url)

            # Should handle exception and return None
            assert result is None
