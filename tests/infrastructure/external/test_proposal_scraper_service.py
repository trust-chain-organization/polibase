"""Unit tests for ProposalScraperService."""

from unittest.mock import AsyncMock, patch

import pytest

from src.infrastructure.external.proposal_scraper_service import (
    ProposalScraperService,
)


class TestProposalScraperService:
    """Test suite for ProposalScraperService."""

    @pytest.fixture
    def scraper(self):
        """Create a ProposalScraperService instance."""
        return ProposalScraperService(headless=True)

    def test_is_supported_url_shugiin(self, scraper):
        """Test that Shugiin URLs are recognized as supported."""
        urls = [
            "https://www.shugiin.go.jp/internet/itdb_gian.nsf/html/gian/honbun/houan/g21009001.htm",
            "http://shugiin.go.jp/some/page",
        ]
        for url in urls:
            assert scraper.is_supported_url(url) is True

    def test_is_supported_url_kyoto(self, scraper):
        """Test that Kyoto City Council URLs are recognized as supported."""
        urls = [
            "https://www.city.kyoto.lg.jp/shikai/page/0000123456.html",
            "https://www.city.kyoto.jp/shikai/proposal.html",
        ]
        for url in urls:
            assert scraper.is_supported_url(url) is True

    def test_is_supported_url_unsupported(self, scraper):
        """Test that unsupported URLs are not recognized."""
        urls = [
            "https://www.google.com",
            "https://www.example.com/proposal",
            "https://www.tokyo.lg.jp/shikai/page.html",
        ]
        for url in urls:
            assert scraper.is_supported_url(url) is False

    @pytest.mark.asyncio
    async def test_scrape_proposal_unsupported_url(self, scraper):
        """Test that scraping unsupported URLs raises ValueError."""
        url = "https://www.google.com"
        with pytest.raises(ValueError, match="Unsupported URL"):
            await scraper.scrape_proposal(url)

    @pytest.mark.asyncio
    @patch("src.infrastructure.external.proposal_scraper_service.async_playwright")
    async def test_scrape_shugiin_proposal(self, mock_playwright, scraper):
        """Test scraping a Shugiin proposal."""
        # Mock the HTML content
        html_content = """
        <html>
            <head><title>第210回国会 第1号 環境基本法改正案</title></head>
            <body>
                <h1>第210回国会 第1号 環境基本法改正案</h1>
                <div>提出日：2023年12月1日</div>
                <div>提出者：山田太郎</div>
                <div>審議状況：審議中</div>
                <div class="summary">この法案は環境保護を強化するものです。</div>
            </body>
        </html>
        """

        # Set up mocks
        mock_browser = AsyncMock()
        mock_page = AsyncMock()
        mock_page.content.return_value = html_content
        mock_browser.new_page.return_value = mock_page

        mock_chromium = AsyncMock()
        mock_chromium.launch.return_value = mock_browser

        mock_p = AsyncMock()
        mock_p.chromium = mock_chromium
        mock_p.__aenter__.return_value = mock_p
        mock_p.__aexit__.return_value = None

        mock_playwright.return_value = mock_p

        # Execute
        url = "https://www.shugiin.go.jp/test"
        result = await scraper.scrape_proposal(url)

        # Assert
        assert result["url"] == url
        assert result["content"] == "環境基本法改正案"
        assert result["proposal_number"] == "第210回国会 第1号"
        assert result["submission_date"] == "2023-12-01"
        assert result["submitter"] == "山田太郎"
        assert result["status"] == "審議中"
        assert result["summary"] == "この法案は環境保護を強化するものです。"

    @pytest.mark.asyncio
    @patch("src.infrastructure.external.proposal_scraper_service.async_playwright")
    async def test_scrape_kyoto_proposal(self, mock_playwright, scraper):
        """Test scraping a Kyoto City Council proposal."""
        # Mock the HTML content
        html_content = """
        <html>
            <head><title>京都市議会議案</title></head>
            <body>
                <h1>京都市観光振興条例の改正について</h1>
                <div>議第15号</div>
                <div>令和5年12月15日</div>
                <div>提出者：市長</div>
                <div>結果：可決</div>
                <div class="概要">観光振興のための条例改正案です。</div>
            </body>
        </html>
        """

        # Set up mocks
        mock_browser = AsyncMock()
        mock_page = AsyncMock()
        mock_page.content.return_value = html_content
        mock_browser.new_page.return_value = mock_page

        mock_chromium = AsyncMock()
        mock_chromium.launch.return_value = mock_browser

        mock_p = AsyncMock()
        mock_p.chromium = mock_chromium
        mock_p.__aenter__.return_value = mock_p
        mock_p.__aexit__.return_value = None

        mock_playwright.return_value = mock_p

        # Execute
        url = "https://www.city.kyoto.lg.jp/test"
        result = await scraper.scrape_proposal(url)

        # Assert
        assert result["url"] == url
        assert result["content"] == "京都市観光振興条例の改正について"
        assert result["proposal_number"] == "議第15号"
        assert result["submission_date"] == "2023-12-15"
        assert result["submitter"] == "市長"
        assert result["status"] == "可決"
        assert "観光振興" in result["summary"]

    def test_convert_japanese_date_to_iso(self, scraper):
        """Test Japanese date conversion to ISO format."""
        # Test standard format
        assert scraper._convert_japanese_date_to_iso("2023年12月1日") == "2023-12-01"
        assert scraper._convert_japanese_date_to_iso("2023年1月15日") == "2023-01-15"

        # Test Reiwa format
        assert scraper._convert_japanese_date_to_iso("令和5年12月1日") == "2023-12-01"
        assert scraper._convert_japanese_date_to_iso("令和1年5月1日") == "2019-05-01"

        # Test Heisei format
        assert scraper._convert_japanese_date_to_iso("平成31年4月30日") == "2019-04-30"
        assert scraper._convert_japanese_date_to_iso("平成元年1月8日") == "1989-01-08"

        # Test invalid format (should return original)
        assert scraper._convert_japanese_date_to_iso("invalid date") == "invalid date"

    @pytest.mark.asyncio
    @patch("src.infrastructure.external.proposal_scraper_service.async_playwright")
    async def test_scrape_proposal_runtime_error(self, mock_playwright, scraper):
        """Test that scraping errors are properly handled."""
        # Set up mocks to raise an exception
        mock_browser = AsyncMock()
        mock_page = AsyncMock()
        mock_page.goto.side_effect = Exception("Network error")
        mock_browser.new_page.return_value = mock_page

        mock_chromium = AsyncMock()
        mock_chromium.launch.return_value = mock_browser

        mock_p = AsyncMock()
        mock_p.chromium = mock_chromium
        mock_p.__aenter__.return_value = mock_p
        mock_p.__aexit__.return_value = None

        mock_playwright.return_value = mock_p

        # Execute and assert
        url = "https://www.shugiin.go.jp/test"
        with pytest.raises(RuntimeError, match="Failed to scrape Shugiin proposal"):
            await scraper.scrape_proposal(url)
