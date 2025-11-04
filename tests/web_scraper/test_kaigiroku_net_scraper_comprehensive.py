"""Comprehensive tests for KaigirokuNetScraper

Following Phase 1 (KokkaiScraper) success pattern with category-based testing.
Focuses on high-coverage methods to reach >80% target from current 31.1%.
"""

from unittest.mock import AsyncMock, patch

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
        from datetime import datetime

        scraper = KaigirokuNetScraper()
        mock_page = AsyncMock()

        # Mock element with text_content
        mock_element = AsyncMock()
        mock_element.text_content = AsyncMock(return_value="令和7年1月23日")
        mock_page.query_selector = AsyncMock(return_value=mock_element)

        # Mock date_parser to return datetime
        expected_date = datetime(2025, 1, 23)
        with patch.object(scraper.date_parser, "parse", return_value=expected_date):
            result = await scraper._extract_date(mock_page)

            assert result == expected_date

    @pytest.mark.asyncio
    async def test_extract_date_heisei_format(self):
        """Test extracting date in Heisei format"""
        from datetime import datetime

        scraper = KaigirokuNetScraper()
        mock_page = AsyncMock()

        mock_element = AsyncMock()
        mock_element.text_content = AsyncMock(return_value="平成16年9月22日")
        mock_page.query_selector = AsyncMock(return_value=mock_element)

        expected_date = datetime(2004, 9, 22)
        with patch.object(scraper.date_parser, "parse", return_value=expected_date):
            result = await scraper._extract_date(mock_page)

            assert result == expected_date

    @pytest.mark.asyncio
    async def test_extract_date_western_format(self):
        """Test extracting date in Western calendar format"""
        from datetime import datetime

        scraper = KaigirokuNetScraper()
        mock_page = AsyncMock()

        mock_element = AsyncMock()
        mock_element.text_content = AsyncMock(return_value="2024年12月31日")
        mock_page.query_selector = AsyncMock(return_value=mock_element)

        expected_date = datetime(2024, 12, 31)
        with patch.object(scraper.date_parser, "parse", return_value=expected_date):
            result = await scraper._extract_date(mock_page)

            assert result == expected_date

    @pytest.mark.asyncio
    async def test_extract_date_no_element(self):
        """Test date extraction when date element not found"""
        scraper = KaigirokuNetScraper()
        mock_page = AsyncMock()
        mock_page.query_selector = AsyncMock(return_value=None)
        mock_page.content = AsyncMock(return_value="<html></html>")

        # Mock date_parser.extract_from_text to return None
        with patch.object(scraper.date_parser, "extract_from_text", return_value=None):
            result = await scraper._extract_date(mock_page)

            assert result is None

    @pytest.mark.asyncio
    async def test_extract_date_invalid_format(self):
        """Test date extraction with invalid date format"""
        scraper = KaigirokuNetScraper()
        mock_page = AsyncMock()

        mock_element = AsyncMock()
        mock_element.text_content = AsyncMock(return_value="Invalid Date")
        mock_page.query_selector = AsyncMock(return_value=mock_element)
        mock_page.content = AsyncMock(return_value="<html>Invalid Date</html>")

        # Mock date_parser to return None for invalid dates
        with patch.object(scraper.date_parser, "parse", return_value=None):
            with patch.object(
                scraper.date_parser, "extract_from_text", return_value=None
            ):
                result = await scraper._extract_date(mock_page)

                assert result is None


class TestKaigirokuNetScraperPDFURLFinding:
    """Test PDF download URL finding"""

    @pytest.mark.asyncio
    async def test_find_pdf_download_url_found_in_buttons(self):
        """Test finding PDF URL in download buttons"""
        scraper = KaigirokuNetScraper()
        mock_page = AsyncMock()
        mock_page.url = "https://ssp.kaigiroku.net/tenant/test/MinuteView.html"

        # Mock element with PDF href
        mock_element = AsyncMock()
        mock_element.get_attribute = AsyncMock(
            return_value="https://example.com/minutes.pdf"
        )
        mock_page.query_selector_all = AsyncMock(return_value=[mock_element])

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
        mock_page.url = "https://ssp.kaigiroku.net/tenant/test/MinuteView.html"

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
        mock_page.wait_for_selector = AsyncMock()  # Succeeds
        mock_page.query_selector_all = AsyncMock(return_value=[])

        # Mock asyncio.sleep to avoid actual waiting
        with patch("asyncio.sleep", AsyncMock()):
            await scraper._wait_for_content(mock_page)

            # Should have tried to wait for selector
            mock_page.wait_for_selector.assert_called()

    @pytest.mark.asyncio
    async def test_wait_for_content_timeout_then_success(self):
        """Test waiting with initial timeout then success"""
        scraper = KaigirokuNetScraper()
        mock_page = AsyncMock()

        # First call times out, second succeeds
        call_count = 0

        def wait_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("Timeout")
            return AsyncMock()

        mock_page.wait_for_selector = AsyncMock(side_effect=wait_side_effect)
        mock_page.query_selector_all = AsyncMock(return_value=[])

        with patch("asyncio.sleep", AsyncMock()):
            await scraper._wait_for_content(mock_page)

            # Should have retried multiple selectors
            assert mock_page.wait_for_selector.call_count >= 2


class TestKaigirokuNetScraperPDFDownload:
    """Test PDF download and minutes creation"""

    @pytest.mark.asyncio
    async def test_download_pdf_as_minutes_success(self):
        """Test successful PDF download and conversion to MinutesData"""
        scraper = KaigirokuNetScraper()

        # Mock PDF handler's download_and_extract method
        with patch.object(
            scraper.pdf_handler,
            "download_and_extract",
            return_value=("/path/to/downloaded.pdf", "PDF content text"),
        ):
            # Mock file_handler's generate_filename
            with patch.object(
                scraper.file_handler,
                "generate_filename",
                return_value="test_123_456.pdf",
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

        # Mock PDF download failure (returns None for path)
        with patch.object(
            scraper.pdf_handler,
            "download_and_extract",
            return_value=(None, ""),
        ):
            with patch.object(
                scraper.file_handler,
                "generate_filename",
                return_value="test_123_456.pdf",
            ):
                result = await scraper._download_pdf_as_minutes(
                    "https://example.com/minutes.pdf",
                    "https://source.url",
                    "123",
                    "456",
                )

                assert result is None


class TestKaigirokuNetScraperErrorHandling:
    """Test error handling in various methods"""

    @pytest.mark.asyncio
    async def test_extract_date_exception_handling(self):
        """Test date extraction handles exceptions gracefully"""
        scraper = KaigirokuNetScraper()
        mock_page = AsyncMock()
        mock_page.query_selector = AsyncMock(side_effect=Exception("Page error"))

        result = await scraper._extract_date(mock_page)

        assert result is None

    @pytest.mark.asyncio
    async def test_find_pdf_url_exception_handling(self):
        """Test PDF URL finding handles exceptions gracefully"""
        scraper = KaigirokuNetScraper()
        mock_page = AsyncMock()
        mock_page.url = "https://test.com/page.html"
        mock_page.query_selector_all = AsyncMock(
            side_effect=Exception("Selector error")
        )

        result = await scraper._find_pdf_download_url(mock_page)

        assert result is None

    @pytest.mark.asyncio
    async def test_find_text_view_url_exception_handling(self):
        """Test text view URL finding handles exceptions gracefully"""
        scraper = KaigirokuNetScraper()
        mock_page = AsyncMock()
        mock_page.url = "https://test.com/page.html"
        mock_page.query_selector = AsyncMock(side_effect=Exception("Selector error"))

        result = await scraper._find_text_view_url(mock_page)

        assert result is None

    @pytest.mark.asyncio
    async def test_download_pdf_exception_handling(self):
        """Test PDF download handles exceptions gracefully"""
        scraper = KaigirokuNetScraper()

        with patch.object(
            scraper.pdf_handler,
            "download_and_extract",
            side_effect=Exception("Download error"),
        ):
            with patch.object(
                scraper.file_handler, "generate_filename", return_value="test.pdf"
            ):
                result = await scraper._download_pdf_as_minutes(
                    "https://example.com/test.pdf", "https://source.com", "1", "2"
                )

                assert result is None


class TestKaigirokuNetScraperPDFURLEdgeCases:
    """Test PDF URL finding edge cases"""

    @pytest.mark.asyncio
    async def test_find_pdf_url_with_onclick_attribute(self):
        """Test PDF URL extraction from onclick attribute"""
        scraper = KaigirokuNetScraper()
        mock_page = AsyncMock()
        mock_page.url = "https://test.com/page.html"

        # Element with onclick containing PDF URL
        mock_element = AsyncMock()
        mock_element.get_attribute = AsyncMock(
            side_effect=lambda attr: (
                None
                if attr == "href"
                else "window.open('document.pdf')"
                if attr == "onclick"
                else None
            )
        )
        mock_page.query_selector_all = AsyncMock(return_value=[mock_element])

        result = await scraper._find_pdf_download_url(mock_page)

        assert result is not None
        assert "document.pdf" in result

    @pytest.mark.asyncio
    async def test_find_pdf_url_relative_path_conversion(self):
        """Test relative PDF URL gets converted to absolute"""
        scraper = KaigirokuNetScraper()
        mock_page = AsyncMock()
        mock_page.url = "https://test.com/tenant/page.html"

        mock_element = AsyncMock()
        mock_element.get_attribute = AsyncMock(return_value="docs/minutes.pdf")
        mock_page.query_selector_all = AsyncMock(return_value=[mock_element])

        result = await scraper._find_pdf_download_url(mock_page)

        assert result is not None
        # URL should contain the relative path and base URL
        assert "test.com" in result
        assert "minutes.pdf" in result


class TestKaigirokuNetScraperWaitForContentEdgeCases:
    """Test wait for content edge cases"""

    @pytest.mark.asyncio
    async def test_wait_for_content_no_selector_found_checks_iframes(self):
        """Test wait_for_content checks for iframes when no selector found"""
        scraper = KaigirokuNetScraper()
        mock_page = AsyncMock()

        # All selectors fail
        mock_page.wait_for_selector = AsyncMock(side_effect=Exception("Not found"))

        # Mock iframes found
        mock_iframe = AsyncMock()
        mock_page.query_selector_all = AsyncMock(return_value=[mock_iframe])

        with patch("asyncio.sleep", AsyncMock()):
            await scraper._wait_for_content(mock_page)

            # Should have checked for iframes
            mock_page.query_selector_all.assert_called_with("iframe")


class TestKaigirokuNetScraperMainFlow:
    """Test main fetch_minutes flow with various scenarios"""

    @pytest.mark.asyncio
    async def test_fetch_minutes_with_pdf_flow(self):
        """Test fetch_minutes when PDF is available"""
        from datetime import datetime

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
                # Mock asyncio.sleep to speed up test
                with patch("asyncio.sleep", AsyncMock()):
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
                                date=datetime(2025, 1, 1),
                                speakers=[],
                                scraped_at=datetime.now(),
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
