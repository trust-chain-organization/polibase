"""Tests for web scraper module"""
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from datetime import datetime
import asyncio

from src.web_scraper.base_scraper import MinutesData
from src.web_scraper.kaigiroku_net_scraper import KaigirokuNetScraper
from src.web_scraper.scraper_service import ScraperService


class TestMinutesData:
    """Test MinutesData class"""
    
    def test_minutes_data_creation(self):
        """Test creating MinutesData object"""
        data = MinutesData(
            council_id="6030",
            schedule_id="1",
            title="令和6年第1回定例会",
            date=datetime(2024, 1, 15),
            content="議事録本文",
            speakers=[{"name": "山田議員", "content": "発言内容"}],
            url="https://example.com/minutes",
            scraped_at=datetime.now()
        )
        
        assert data.council_id == "6030"
        assert data.schedule_id == "1"
        assert data.title == "令和6年第1回定例会"
        assert len(data.speakers) == 1
        assert data.speakers[0]["name"] == "山田議員"
    
    def test_minutes_data_to_dict(self):
        """Test converting MinutesData to dictionary"""
        scraped_at = datetime.now()
        data = MinutesData(
            council_id="6030",
            schedule_id="1",
            title="Test",
            date=datetime(2024, 1, 1),
            content="Content",
            speakers=[],
            url="https://example.com",
            scraped_at=scraped_at,
            pdf_url="https://example.com/test.pdf"
        )
        
        result = data.to_dict()
        assert isinstance(result, dict)
        assert result["council_id"] == "6030"
        assert result["pdf_url"] == "https://example.com/test.pdf"
        assert result["date"] == datetime(2024, 1, 1).isoformat()
        assert result["scraped_at"] == scraped_at.isoformat()


class TestKaigirokuNetScraper:
    """Test KaigirokuNetScraper class"""
    
    def test_parse_japanese_date(self):
        """Test parsing Japanese date strings"""
        scraper = KaigirokuNetScraper()
        
        # 令和の日付
        date1 = scraper.parse_japanese_date("令和6年12月20日")
        assert date1 == datetime(2024, 12, 20)
        
        # 平成の日付
        date2 = scraper.parse_japanese_date("平成31年4月1日")
        assert date2 == datetime(2019, 4, 1)
        
        # 西暦の日付
        date3 = scraper.parse_japanese_date("2024年1月15日")
        assert date3 == datetime(2024, 1, 15)
        
        # 無効な日付
        date4 = scraper.parse_japanese_date("invalid date")
        assert date4 is None
    
    @pytest.mark.asyncio
    async def test_extract_minutes_text(self):
        """Test extracting minutes text from HTML"""
        scraper = KaigirokuNetScraper()
        
        html = """
        <html>
        <body>
            <div id="plain-minute">
                <p>これは議事録の本文です。</p>
                <p>複数の段落があります。</p>
            </div>
        </body>
        </html>
        """
        
        result = await scraper.extract_minutes_text(html)
        assert "これは議事録の本文です。" in result
        assert "複数の段落があります。" in result
    
    @pytest.mark.asyncio
    async def test_extract_speakers(self):
        """Test extracting speaker information from HTML"""
        scraper = KaigirokuNetScraper()
        
        html = """
        <html>
        <body>
            <div>
                【山田太郎議員】これは山田議員の発言です。
                続きの発言内容。
                
                ○佐藤花子委員：これは佐藤委員の発言です。
                
                市長：市長の発言です。
            </div>
        </body>
        </html>
        """
        
        speakers = await scraper.extract_speakers(html)
        assert len(speakers) >= 2
        assert any(s["name"] == "山田太郎議員" for s in speakers)
        assert any("佐藤花子委員" in s["name"] for s in speakers)


class TestScraperService:
    """Test ScraperService class"""
    
    @pytest.mark.asyncio
    async def test_fetch_from_url_with_cache(self):
        """Test fetching from URL with cache"""
        service = ScraperService()
        
        # Mock cache
        mock_minutes = MinutesData(
            council_id="6030",
            schedule_id="1",
            title="Cached",
            date=datetime.now(),
            content="Cached content",
            speakers=[],
            url="https://example.com",
            scraped_at=datetime.now()
        )
        
        with patch.object(service, '_get_from_cache', return_value=mock_minutes):
            result = await service.fetch_from_url("https://example.com", use_cache=True)
            assert result.title == "Cached"
    
    @pytest.mark.asyncio
    async def test_fetch_multiple(self):
        """Test fetching multiple URLs"""
        service = ScraperService()
        
        urls = [
            "https://example.com/1",
            "https://example.com/2",
            "https://example.com/3"
        ]
        
        # Mock fetch_from_url
        async def mock_fetch(url):
            return MinutesData(
                council_id=url.split('/')[-1],
                schedule_id="1",
                title=f"Minutes {url.split('/')[-1]}",
                date=datetime.now(),
                content="Content",
                speakers=[],
                url=url,
                scraped_at=datetime.now()
            )
        
        with patch.object(service, 'fetch_from_url', side_effect=mock_fetch):
            results = await service.fetch_multiple(urls, max_concurrent=2)
            assert len(results) == 3
            assert all(r is not None for r in results)
    
    def test_export_to_text(self):
        """Test exporting to text file"""
        import tempfile
        import os
        
        service = ScraperService()
        
        minutes = MinutesData(
            council_id="6030",
            schedule_id="1",
            title="テスト議事録",
            date=datetime(2024, 1, 15),
            content="これは議事録の本文です。",
            speakers=[
                {"name": "山田議員", "content": "山田の発言"},
                {"name": "佐藤議員", "content": "佐藤の発言"}
            ],
            url="https://example.com",
            scraped_at=datetime.now()
        )
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            temp_path = f.name
        
        try:
            result = service.export_to_text(minutes, temp_path)
            assert result is True
            
            # ファイルの内容を確認
            with open(temp_path, 'r', encoding='utf-8') as f:
                content = f.read()
                assert "テスト議事録" in content
                assert "2024年01月15日" in content
                assert "これは議事録の本文です。" in content
                assert "山田議員" in content
                assert "山田の発言" in content
        finally:
            os.unlink(temp_path)